"""Tests for LiveOrderBook and live orderbook wiring in OrderBookAnalyzer"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from polyterm.core.orderbook import (
    LiveOrderBook,
    OrderBookAnalyzer,
    OrderBookAnalysis,
    OrderBookLevel,
)
from polyterm.api.clob import CLOBClient


# ── LiveOrderBook unit tests ──────────────────────────────────────────────


class TestLiveOrderBookInit:
    """Test LiveOrderBook initialization"""

    def test_init_defaults(self):
        book = LiveOrderBook("token-abc")
        assert book.token_id == "token-abc"
        assert not book.is_ready
        assert book.message_count == 0
        assert book.last_update is None

    def test_empty_snapshot(self):
        book = LiveOrderBook("t1")
        snap = book.get_snapshot()
        assert snap["bids"] == []
        assert snap["asks"] == []
        assert snap["last_trade_price"] is None
        assert snap["message_count"] == 0

    def test_empty_top_of_book(self):
        book = LiveOrderBook("t1")
        tob = book.get_top_of_book()
        assert tob["best_bid"] is None
        assert tob["best_ask"] is None
        assert tob["spread"] is None
        assert tob["mid_price"] is None


class TestLiveOrderBookMessages:
    """Test handling of WebSocket messages"""

    def _make_book_msg(self, bids=None, asks=None):
        return {
            "type": "book",
            "market": "token-1",
            "bids": bids or [],
            "asks": asks or [],
        }

    def test_book_message_populates_levels(self):
        book = LiveOrderBook("token-1")
        book.handle_message(self._make_book_msg(
            bids=[{"price": "0.55", "size": "1200"}, {"price": "0.54", "size": "800"}],
            asks=[{"price": "0.56", "size": "600"}, {"price": "0.57", "size": "400"}],
        ))
        assert book.is_ready
        assert book.message_count == 1

        tob = book.get_top_of_book()
        assert tob["best_bid"] == 0.55
        assert tob["best_ask"] == 0.56
        assert tob["spread"] == pytest.approx(0.01)
        assert tob["mid_price"] == pytest.approx(0.555)

    def test_incremental_book_update(self):
        book = LiveOrderBook("token-1")
        # Initial snapshot
        book.handle_message(self._make_book_msg(
            bids=[{"price": "0.55", "size": "1000"}],
            asks=[{"price": "0.56", "size": "500"}],
        ))
        # Incremental update — add new bid level, update ask
        book.handle_message(self._make_book_msg(
            bids=[{"price": "0.54", "size": "2000"}],
            asks=[{"price": "0.56", "size": "800"}],
        ))

        snap = book.get_snapshot()
        # Should have 2 bid levels now
        assert len(snap["bids"]) == 2
        # Ask size should be updated
        ask_56 = next(a for a in snap["asks"] if a["price"] == "0.56")
        assert ask_56["size"] == "800"

    def test_level_removal_on_zero_size(self):
        book = LiveOrderBook("token-1")
        book.handle_message(self._make_book_msg(
            bids=[{"price": "0.55", "size": "1000"}, {"price": "0.54", "size": "500"}],
            asks=[],
        ))
        assert len(book.get_snapshot()["bids"]) == 2

        # Remove the 0.55 level
        book.handle_message(self._make_book_msg(
            bids=[{"price": "0.55", "size": "0"}],
        ))
        bids = book.get_snapshot()["bids"]
        assert len(bids) == 1
        assert bids[0]["price"] == "0.54"

    def test_last_trade_price_message(self):
        book = LiveOrderBook("token-1")
        book.handle_message({
            "type": "last_trade_price",
            "market": "token-1",
            "price": "0.552",
        })
        assert book.message_count == 1
        tob = book.get_top_of_book()
        assert tob["last_trade_price"] == 0.552

    def test_price_change_message(self):
        book = LiveOrderBook("token-1")
        book.handle_message({
            "type": "price_change",
            "market": "token-1",
            "price": "0.56",
        })
        snap = book.get_snapshot()
        assert snap["last_price_change"] == 0.56

    def test_unknown_message_type_increments_count(self):
        book = LiveOrderBook("token-1")
        book.handle_message({"type": "tick_size_change", "market": "token-1"})
        assert book.message_count == 1
        # But no book data
        assert not book.is_ready

    def test_on_update_callback_fires(self):
        book = LiveOrderBook("token-1")
        callback = Mock()
        book.set_on_update(callback)
        book.handle_message(self._make_book_msg(
            bids=[{"price": "0.55", "size": "100"}],
        ))
        callback.assert_called_once_with(book)

    def test_on_update_callback_exception_suppressed(self):
        book = LiveOrderBook("token-1")
        book.set_on_update(Mock(side_effect=ValueError("boom")))
        # Should not raise
        book.handle_message(self._make_book_msg(
            bids=[{"price": "0.55", "size": "100"}],
        ))
        assert book.message_count == 1

    def test_empty_price_entries_skipped(self):
        book = LiveOrderBook("token-1")
        book.handle_message(self._make_book_msg(
            bids=[{"price": "", "size": "100"}, {"price": "0.55", "size": "100"}],
        ))
        assert len(book.get_snapshot()["bids"]) == 1


class TestLiveOrderBookDepth:
    """Test depth and snapshot queries"""

    @pytest.fixture
    def populated_book(self):
        book = LiveOrderBook("token-1")
        book.handle_message({
            "type": "book",
            "market": "token-1",
            "bids": [
                {"price": "0.55", "size": "1000"},
                {"price": "0.54", "size": "2000"},
                {"price": "0.53", "size": "3000"},
            ],
            "asks": [
                {"price": "0.56", "size": "800"},
                {"price": "0.57", "size": "1500"},
                {"price": "0.58", "size": "2500"},
            ],
        })
        return book

    def test_snapshot_bids_sorted_descending(self, populated_book):
        snap = populated_book.get_snapshot()
        prices = [float(b["price"]) for b in snap["bids"]]
        assert prices == [0.55, 0.54, 0.53]

    def test_snapshot_asks_sorted_ascending(self, populated_book):
        snap = populated_book.get_snapshot()
        prices = [float(a["price"]) for a in snap["asks"]]
        assert prices == [0.56, 0.57, 0.58]

    def test_get_depth_limits_levels(self, populated_book):
        depth = populated_book.get_depth(levels=2)
        assert len(depth["bids"]) == 2
        assert len(depth["asks"]) == 2

    def test_get_depth_cumulative_sizes(self, populated_book):
        depth = populated_book.get_depth(levels=3)
        # Bids cumulative: 1000, 3000, 6000
        assert depth["bids"][0]["cumulative_size"] == 1000.0
        assert depth["bids"][1]["cumulative_size"] == 3000.0
        assert depth["bids"][2]["cumulative_size"] == 6000.0
        assert depth["bid_depth"] == 6000.0

    def test_get_depth_ask_cumulative(self, populated_book):
        depth = populated_book.get_depth(levels=3)
        assert depth["asks"][0]["cumulative_size"] == 800.0
        assert depth["asks"][1]["cumulative_size"] == 2300.0
        assert depth["ask_depth"] == 4800.0

    def test_timestamp_updated(self, populated_book):
        assert populated_book.last_update is not None
        assert isinstance(populated_book.last_update, datetime)


# ── OrderBookAnalyzer live methods ────────────────────────────────────────


class TestAnalyzerLiveFeed:
    """Test OrderBookAnalyzer.start_live_feed and related methods"""

    @pytest.fixture
    def clob_client(self):
        client = MagicMock(spec=CLOBClient)
        client.subscribe_orderbook = AsyncMock()
        client.listen_orderbook = AsyncMock()
        client.close_websocket = AsyncMock()
        return client

    @pytest.fixture
    def analyzer(self, clob_client):
        return OrderBookAnalyzer(clob_client)

    @pytest.mark.asyncio
    async def test_start_live_feed_creates_books(self, analyzer, clob_client):
        """start_live_feed creates LiveOrderBook instances and subscribes"""
        books = await analyzer.start_live_feed(["token-a", "token-b"])
        assert "token-a" in books
        assert "token-b" in books
        assert isinstance(books["token-a"], LiveOrderBook)
        clob_client.subscribe_orderbook.assert_awaited_once()
        # Verify token IDs passed
        call_args = clob_client.subscribe_orderbook.call_args
        assert call_args[0][0] == ["token-a", "token-b"]

    @pytest.mark.asyncio
    async def test_start_live_feed_dispatch_routes_by_market(self, analyzer, clob_client):
        """WS dispatch callback routes messages to correct book"""
        books = await analyzer.start_live_feed(["token-a", "token-b"])
        # Get the dispatch function that was passed to subscribe_orderbook
        dispatch = clob_client.subscribe_orderbook.call_args[0][1]

        dispatch({
            "type": "book",
            "market": "token-a",
            "bids": [{"price": "0.60", "size": "500"}],
            "asks": [],
        })
        assert books["token-a"].is_ready
        assert not books["token-b"].is_ready

    @pytest.mark.asyncio
    async def test_start_live_feed_dispatch_broadcasts_unknown_market(self, analyzer, clob_client):
        """WS dispatch broadcasts to all books when market is unknown"""
        books = await analyzer.start_live_feed(["token-a", "token-b"])
        dispatch = clob_client.subscribe_orderbook.call_args[0][1]

        dispatch({
            "type": "book",
            "market": "unknown-token",
            "bids": [{"price": "0.50", "size": "100"}],
            "asks": [],
        })
        # Both books should have received it
        assert books["token-a"].is_ready
        assert books["token-b"].is_ready

    @pytest.mark.asyncio
    async def test_start_live_feed_on_update_callback(self, analyzer, clob_client):
        """on_update callback fires for each book update"""
        updates = []
        books = await analyzer.start_live_feed(
            ["token-a"],
            on_update=lambda b: updates.append(b.token_id),
        )
        dispatch = clob_client.subscribe_orderbook.call_args[0][1]
        dispatch({
            "type": "book",
            "market": "token-a",
            "bids": [{"price": "0.50", "size": "100"}],
            "asks": [],
        })
        assert updates == ["token-a"]

    def test_get_live_book_returns_none_before_start(self, analyzer):
        assert analyzer.get_live_book("token-x") is None

    @pytest.mark.asyncio
    async def test_get_live_book_returns_after_start(self, analyzer, clob_client):
        await analyzer.start_live_feed(["token-x"])
        book = analyzer.get_live_book("token-x")
        assert book is not None
        assert book.token_id == "token-x"

    def test_stop_live_feed_clears_books(self, analyzer):
        analyzer._live_books["token-1"] = LiveOrderBook("token-1")
        analyzer.stop_live_feed()
        assert analyzer.get_live_book("token-1") is None


class TestAnalyzerAnalyzeLive:
    """Test OrderBookAnalyzer.analyze_live"""

    @pytest.fixture
    def analyzer(self):
        client = MagicMock(spec=CLOBClient)
        return OrderBookAnalyzer(client)

    def test_analyze_live_returns_none_when_no_book(self, analyzer):
        assert analyzer.analyze_live("nonexistent") is None

    def test_analyze_live_returns_none_when_not_ready(self, analyzer):
        analyzer._live_books["t1"] = LiveOrderBook("t1")
        assert analyzer.analyze_live("t1") is None

    def test_analyze_live_returns_analysis(self, analyzer):
        book = LiveOrderBook("t1")
        book.handle_message({
            "type": "book",
            "market": "t1",
            "bids": [{"price": "0.55", "size": "1000"}, {"price": "0.54", "size": "2000"}],
            "asks": [{"price": "0.56", "size": "800"}, {"price": "0.57", "size": "1200"}],
        })
        analyzer._live_books["t1"] = book

        analysis = analyzer.analyze_live("t1")
        assert analysis is not None
        assert isinstance(analysis, OrderBookAnalysis)
        assert analysis.best_bid == 0.55
        assert analysis.best_ask == 0.56
        assert analysis.spread == pytest.approx(0.01)
        assert analysis.mid_price == pytest.approx(0.555)


class TestAnalyzerGetLivePrices:
    """Test OrderBookAnalyzer.get_live_prices for arb scanner interface"""

    @pytest.fixture
    def analyzer(self):
        client = MagicMock(spec=CLOBClient)
        return OrderBookAnalyzer(client)

    def test_empty_when_no_live_books(self, analyzer):
        result = analyzer.get_live_prices(["t1", "t2"])
        assert result == {}

    def test_returns_only_ready_books(self, analyzer):
        ready = LiveOrderBook("t1")
        ready.handle_message({
            "type": "book", "market": "t1",
            "bids": [{"price": "0.55", "size": "1000"}],
            "asks": [{"price": "0.56", "size": "800"}],
        })
        not_ready = LiveOrderBook("t2")

        analyzer._live_books["t1"] = ready
        analyzer._live_books["t2"] = not_ready

        result = analyzer.get_live_prices(["t1", "t2"])
        assert "t1" in result
        assert "t2" not in result
        assert result["t1"]["best_bid"] == 0.55
        assert result["t1"]["best_ask"] == 0.56
        assert result["t1"]["spread"] == pytest.approx(0.01)

    def test_ignores_unknown_tokens(self, analyzer):
        result = analyzer.get_live_prices(["unknown"])
        assert result == {}


class TestAnalyzerAnalyzeSnapshot:
    """Test the shared _analyze_snapshot method"""

    @pytest.fixture
    def analyzer(self):
        client = MagicMock(spec=CLOBClient)
        return OrderBookAnalyzer(client)

    def test_returns_none_for_empty_book(self, analyzer):
        assert analyzer._analyze_snapshot("m1", {"bids": [], "asks": []}) is None

    def test_returns_none_for_missing_side(self, analyzer):
        assert analyzer._analyze_snapshot("m1", {
            "bids": [{"price": "0.5", "size": "100"}], "asks": []
        }) is None

    def test_basic_analysis_from_snapshot(self, analyzer):
        result = analyzer._analyze_snapshot("m1", {
            "bids": [{"price": "0.50", "size": "500"}],
            "asks": [{"price": "0.60", "size": "300"}],
        })
        assert result is not None
        assert result.best_bid == 0.50
        assert result.best_ask == 0.60
        assert result.spread == pytest.approx(0.10)
        assert result.mid_price == pytest.approx(0.55)

    def test_wide_spread_warning(self, analyzer):
        result = analyzer._analyze_snapshot("m1", {
            "bids": [{"price": "0.30", "size": "100"}],
            "asks": [{"price": "0.70", "size": "100"}],
        })
        assert any("Wide spread" in w for w in result.warnings)

    def test_imbalance_warning(self, analyzer):
        result = analyzer._analyze_snapshot("m1", {
            "bids": [{"price": "0.50", "size": "10000"}],
            "asks": [{"price": "0.51", "size": "100"}],
        })
        assert any("imbalance" in w for w in result.warnings)

    def test_large_order_detection(self, analyzer):
        # Default threshold is $10,000
        result = analyzer._analyze_snapshot("m1", {
            "bids": [{"price": "0.50", "size": "25000"}],  # 25000 * 0.50 = $12,500
            "asks": [{"price": "0.51", "size": "100"}],
        })
        assert len(result.large_bids) == 1
        assert result.large_bids[0].size == 25000.0


# ── CLI --live flag tests ─────────────────────────────────────────────────


class TestOrderbookCLILiveFlag:
    """Test the --live flag on the orderbook CLI command"""

    def test_cli_has_live_option(self):
        """Verify the --live flag is registered"""
        from polyterm.cli.commands.orderbook import orderbook
        param_names = [p.name for p in orderbook.params]
        assert "live" in param_names

    def test_cli_has_refresh_option(self):
        """Verify the --refresh option is registered"""
        from polyterm.cli.commands.orderbook import orderbook
        param_names = [p.name for p in orderbook.params]
        assert "refresh" in param_names
