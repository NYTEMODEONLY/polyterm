"""Tests for real-time settlement detection via CLOB WebSocket market_resolved event (POL-13)"""

import json
import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from polyterm.core.orderbook import LiveOrderBook, OrderBookAnalyzer
from polyterm.db.database import Database
from polyterm.db.models import ResolutionOutcome


# ---------------------------------------------------------------------------
# LiveOrderBook resolution tests
# ---------------------------------------------------------------------------

class TestLiveOrderBookResolution:
    """Test LiveOrderBook handles market_resolved messages correctly."""

    def test_initial_state_not_resolved(self):
        book = LiveOrderBook("token123")
        assert book.resolved is False
        assert book.resolution_data is None

    def test_handle_market_resolved_message(self):
        book = LiveOrderBook("token123")
        msg = {
            "type": "market_resolved",
            "market": "token123",
            "outcome": "YES",
            "price": "1.0",
        }
        book.handle_message(msg)

        assert book.resolved is True
        data = book.resolution_data
        assert data is not None
        assert data["outcome"] == "YES"
        assert data["winning_price"] == 1.0
        assert data["token_id"] == "token123"
        assert isinstance(data["resolved_at"], datetime)

    def test_handle_market_resolved_no_outcome(self):
        book = LiveOrderBook("token456")
        msg = {
            "type": "market_resolved",
            "market": "token456",
            "outcome": "NO",
            "winning_price": "1.0",
        }
        book.handle_message(msg)

        assert book.resolved is True
        assert book.resolution_data["outcome"] == "NO"

    def test_handle_market_resolved_missing_price(self):
        book = LiveOrderBook("token789")
        msg = {
            "type": "market_resolved",
            "market": "token789",
            "outcome": "YES",
        }
        book.handle_message(msg)

        assert book.resolved is True
        # Should default to 1.0
        assert book.resolution_data["winning_price"] == 1.0

    def test_resolution_does_not_break_normal_messages(self):
        book = LiveOrderBook("token123")

        # Normal book message
        book_msg = {
            "type": "book",
            "market": "token123",
            "bids": [{"price": "0.55", "size": "100"}],
            "asks": [{"price": "0.56", "size": "100"}],
        }
        book.handle_message(book_msg)
        assert book.resolved is False
        assert book.message_count == 1

        # Resolution
        res_msg = {"type": "market_resolved", "market": "token123", "outcome": "YES"}
        book.handle_message(res_msg)
        assert book.resolved is True
        assert book.message_count == 2


# ---------------------------------------------------------------------------
# CLOBClient WebSocket resolution callback tests
# ---------------------------------------------------------------------------

class TestCLOBClientResolutionCallback:
    """Test that listen_orderbook routes market_resolved to the resolution callback."""

    @pytest.fixture
    def client(self):
        from polyterm.api.clob import CLOBClient
        return CLOBClient(
            rest_endpoint="https://clob.example.com",
            ws_endpoint="wss://ws.example.com",
        )

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    async def test_market_resolved_invokes_resolution_callback(self, client):
        """market_resolved messages should invoke _ob_resolution_callback, not _ob_callback."""
        ob_messages = []
        res_messages = []

        def ob_callback(data):
            ob_messages.append(data)

        def res_callback(data):
            res_messages.append(data)

        resolved_msg = json.dumps({
            "type": "market_resolved",
            "market": "token1",
            "outcome": "YES",
            "price": "1.0",
        })

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[resolved_msg, Exception("done")])

        client.clob_ws = mock_ws
        client._ob_callback = ob_callback
        client._ob_resolution_callback = res_callback

        await client.listen_orderbook(max_reconnects=0)

        # Resolution callback should receive the message
        assert len(res_messages) == 1
        assert res_messages[0]["type"] == "market_resolved"
        assert res_messages[0]["outcome"] == "YES"

        # Normal callback should NOT receive it
        assert len(ob_messages) == 0

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    async def test_market_resolved_without_resolution_callback(self, client):
        """market_resolved messages should be silently ignored when no resolution callback is set."""
        ob_messages = []

        def ob_callback(data):
            ob_messages.append(data)

        resolved_msg = json.dumps({
            "type": "market_resolved",
            "market": "token1",
            "outcome": "YES",
        })
        book_msg = json.dumps({
            "type": "book",
            "market": "token1",
            "bids": [],
            "asks": [],
        })

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[resolved_msg, book_msg, Exception("done")])

        client.clob_ws = mock_ws
        client._ob_callback = ob_callback
        client._ob_resolution_callback = None

        await client.listen_orderbook(max_reconnects=0)

        # Only the book message should reach the ob callback
        assert len(ob_messages) == 1
        assert ob_messages[0]["type"] == "book"

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_subscribe_orderbook_sets_resolution_callback(self, mock_websockets, client):
        """subscribe_orderbook should store the resolution_callback."""
        mock_ws = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)
        client.clob_ws = mock_ws

        res_cb = MagicMock()
        await client.subscribe_orderbook(["t1"], MagicMock(), resolution_callback=res_cb)

        assert client._ob_resolution_callback is res_cb

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_subscribe_sends_custom_feature_enabled(self, mock_websockets, client):
        """Subscription message should include custom_feature_enabled: true."""
        mock_ws = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)
        client.clob_ws = mock_ws

        await client.subscribe_orderbook(["t1", "t2"], MagicMock())

        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["custom_feature_enabled"] is True


# ---------------------------------------------------------------------------
# Database resolution storage tests
# ---------------------------------------------------------------------------

class TestDatabaseResolution:
    """Test database resolution CRUD operations."""

    @pytest.fixture
    def temp_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            yield db

    def test_save_and_get_resolution(self, temp_db):
        resolution = ResolutionOutcome(
            market_id="market_123",
            market_slug="will-btc-reach-100k",
            title="Will BTC reach $100K?",
            resolved=True,
            outcome="YES",
            winning_price=1.0,
            resolved_at=datetime(2026, 3, 30, 12, 0, 0),
            resolution_source="clob_ws",
            fetched_at=datetime.now(),
        )
        temp_db.save_resolution(resolution)

        result = temp_db.get_resolution("market_123")
        assert result is not None
        assert result.market_id == "market_123"
        assert result.resolved is True
        assert result.outcome == "YES"
        assert result.winning_price == 1.0
        assert result.resolution_source == "clob_ws"

    def test_save_resolution_upsert(self, temp_db):
        """Saving again for the same market_id should update, not duplicate."""
        r1 = ResolutionOutcome(
            market_id="market_456",
            resolved=False,
            outcome="",
            fetched_at=datetime.now(),
        )
        temp_db.save_resolution(r1)
        assert temp_db.get_resolution("market_456").resolved is False

        r2 = ResolutionOutcome(
            market_id="market_456",
            resolved=True,
            outcome="NO",
            winning_price=1.0,
            resolved_at=datetime(2026, 3, 30, 14, 0, 0),
            resolution_source="clob_ws",
            fetched_at=datetime.now(),
        )
        temp_db.save_resolution(r2)

        result = temp_db.get_resolution("market_456")
        assert result.resolved is True
        assert result.outcome == "NO"

    def test_get_resolution_not_found(self, temp_db):
        assert temp_db.get_resolution("nonexistent") is None

    def test_get_recent_resolutions(self, temp_db):
        for i in range(5):
            r = ResolutionOutcome(
                market_id=f"market_{i}",
                resolved=True,
                outcome="YES",
                resolved_at=datetime(2026, 3, 30, 10 + i, 0, 0),
                fetched_at=datetime.now(),
            )
            temp_db.save_resolution(r)

        recent = temp_db.get_recent_resolutions(limit=3)
        assert len(recent) == 3
        # Should be ordered by resolved_at descending
        assert recent[0].market_id == "market_4"
        assert recent[2].market_id == "market_2"

    def test_get_recent_resolutions_excludes_unresolved(self, temp_db):
        temp_db.save_resolution(ResolutionOutcome(
            market_id="resolved_1", resolved=True, outcome="YES",
            resolved_at=datetime.now(), fetched_at=datetime.now(),
        ))
        temp_db.save_resolution(ResolutionOutcome(
            market_id="unresolved_1", resolved=False, outcome="",
            fetched_at=datetime.now(),
        ))

        recent = temp_db.get_recent_resolutions()
        assert len(recent) == 1
        assert recent[0].market_id == "resolved_1"


# ---------------------------------------------------------------------------
# OrderBookAnalyzer resolution dispatch tests
# ---------------------------------------------------------------------------

class TestOrderBookAnalyzerResolution:
    """Test that start_live_feed wires the resolution callback correctly."""

    @pytest.mark.asyncio
    async def test_start_live_feed_passes_resolution_callback(self):
        """start_live_feed should pass resolution_callback to subscribe_orderbook."""
        mock_clob = MagicMock()
        mock_clob.subscribe_orderbook = AsyncMock()

        analyzer = OrderBookAnalyzer(mock_clob)
        res_cb = MagicMock()
        await analyzer.start_live_feed(["t1"], on_resolution=res_cb)

        # subscribe_orderbook should have been called with a resolution_callback
        call_kwargs = mock_clob.subscribe_orderbook.call_args
        assert call_kwargs.kwargs.get("resolution_callback") is not None

    @pytest.mark.asyncio
    async def test_start_live_feed_no_resolution_callback_default(self):
        """start_live_feed without on_resolution should pass None."""
        mock_clob = MagicMock()
        mock_clob.subscribe_orderbook = AsyncMock()

        analyzer = OrderBookAnalyzer(mock_clob)
        await analyzer.start_live_feed(["t1"])

        call_kwargs = mock_clob.subscribe_orderbook.call_args
        assert call_kwargs.kwargs.get("resolution_callback") is None

    @pytest.mark.asyncio
    async def test_resolution_dispatch_updates_live_book(self):
        """Resolution dispatch should update the LiveOrderBook state."""
        mock_clob = MagicMock()

        # Capture the dispatchers passed to subscribe_orderbook
        captured_callbacks = {}

        async def fake_subscribe(token_ids, dispatch, resolution_callback=None):
            captured_callbacks["dispatch"] = dispatch
            captured_callbacks["resolution"] = resolution_callback

        mock_clob.subscribe_orderbook = fake_subscribe

        res_events = []
        analyzer = OrderBookAnalyzer(mock_clob)
        books = await analyzer.start_live_feed(
            ["t1"],
            on_resolution=lambda data: res_events.append(data),
        )

        # Simulate a market_resolved message
        res_msg = {"type": "market_resolved", "market": "t1", "outcome": "YES", "price": "1.0"}
        captured_callbacks["resolution"](res_msg)

        # The live book should now be resolved
        assert books["t1"].resolved is True
        assert books["t1"].resolution_data["outcome"] == "YES"

        # The user callback should also have been called
        assert len(res_events) == 1
        assert res_events[0]["outcome"] == "YES"
