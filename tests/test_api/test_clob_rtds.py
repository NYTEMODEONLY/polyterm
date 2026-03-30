"""Tests for CLOB RTDS WebSocket functionality"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch, PropertyMock

from polyterm.api.clob import CLOBClient


class TestCLOBRTDSConnection:
    """Tests for RTDS WebSocket connection lifecycle"""

    @pytest.fixture
    def client(self):
        return CLOBClient(
            rest_endpoint="https://clob.polymarket.com",
            ws_endpoint="wss://ws-live-data.polymarket.com",
        )

    @pytest.mark.asyncio
    async def test_connect_websocket_success(self, client):
        """connect_websocket establishes RTDS connection"""
        mock_ws = AsyncMock()
        with patch("polyterm.api.clob.websockets") as mock_websockets:
            mock_websockets.connect = AsyncMock(return_value=mock_ws)
            result = await client.connect_websocket()
            assert result is True
            assert client.ws_connection is mock_ws
            mock_websockets.connect.assert_awaited_once_with(client.ws_endpoint)

    @pytest.mark.asyncio
    async def test_connect_websocket_without_websockets_raises(self, client):
        """connect_websocket raises when websockets library missing"""
        with patch("polyterm.api.clob.HAS_WEBSOCKETS", False):
            with pytest.raises(Exception, match="websockets library not installed"):
                await client.connect_websocket()

    @pytest.mark.asyncio
    async def test_connect_websocket_connection_failure(self, client):
        """connect_websocket wraps connection errors"""
        with patch("polyterm.api.clob.websockets") as mock_websockets:
            mock_websockets.connect = AsyncMock(side_effect=OSError("refused"))
            with pytest.raises(Exception, match="Failed to connect to WebSocket"):
                await client.connect_websocket()


class TestCLOBRTDSSubscription:
    """Tests for RTDS trade subscription"""

    @pytest.fixture
    def client(self):
        c = CLOBClient()
        c.ws_connection = AsyncMock()
        return c

    @pytest.mark.asyncio
    async def test_subscribe_sends_correct_message(self, client):
        """subscribe_to_trades sends activity/trades subscription"""
        callback = Mock()
        await client.subscribe_to_trades(["btc-100k", "eth-5k"], callback)

        sent = json.loads(client.ws_connection.send.call_args[0][0])
        assert sent["action"] == "subscribe"
        assert sent["subscriptions"] == [{"topic": "activity", "type": "trades"}]

    @pytest.mark.asyncio
    async def test_subscribe_stores_callbacks_by_slug(self, client):
        """subscribe_to_trades stores callbacks keyed by slug"""
        callback = Mock()
        await client.subscribe_to_trades(["btc-100k", "eth-5k"], callback)

        assert client.subscriptions["btc-100k"] is callback
        assert client.subscriptions["eth-5k"] is callback

    @pytest.mark.asyncio
    async def test_subscribe_empty_slugs_stores_all_key(self, client):
        """subscribe_to_trades with no slugs registers _all callback"""
        callback = Mock()
        await client.subscribe_to_trades([], callback)
        assert "_all" in client.subscriptions
        assert client.subscriptions["_all"] is callback

    @pytest.mark.asyncio
    async def test_subscribe_auto_connects_if_no_connection(self):
        """subscribe_to_trades calls connect_websocket when not connected"""
        client = CLOBClient()
        client.ws_connection = None

        mock_ws = AsyncMock()
        with patch("polyterm.api.clob.websockets") as mock_websockets:
            mock_websockets.connect = AsyncMock(return_value=mock_ws)
            await client.subscribe_to_trades(["slug1"], Mock())

        assert client.ws_connection is mock_ws


class TestCLOBRTDSListenForTrades:
    """Tests for listen_for_trades message handling"""

    @pytest.fixture
    def client(self):
        c = CLOBClient()
        return c

    def _make_trade_message(self, event_slug="btc-100k", slug="will-btc-hit-100k"):
        """Helper to create a trade message"""
        return json.dumps({
            "topic": "activity",
            "type": "trades",
            "payload": {
                "eventSlug": event_slug,
                "slug": slug,
                "price": "0.65",
                "size": "100",
            }
        })

    @pytest.mark.asyncio
    async def test_ping_pong_handling(self, client):
        """Server PING message gets PONG response"""
        mock_ws = AsyncMock()
        # Simulate: PING, then ConnectionClosed to exit
        import websockets.exceptions
        mock_ws.__aiter__ = Mock(return_value=iter(["PING"]))
        mock_ws.send = AsyncMock()

        # After iterating, raise ConnectionClosed to break loop
        async def aiter_then_close():
            yield "PING"
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws.__aiter__ = lambda self: aiter_then_close()
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        await client.listen_for_trades(max_reconnects=0)
        mock_ws.send.assert_awaited_with("PONG")

    @pytest.mark.asyncio
    async def test_trade_message_dispatches_to_callback(self, client):
        """Trade message routes to matching subscription callback"""
        callback = Mock(return_value=None)
        trade_msg = self._make_trade_message(event_slug="btc-100k")

        import websockets.exceptions

        async def aiter_messages():
            yield trade_msg
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_messages()
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        await client.listen_for_trades(max_reconnects=0)

        callback.assert_called_once()
        call_data = callback.call_args[0][0]
        assert call_data["topic"] == "activity"
        assert call_data["payload"]["eventSlug"] == "btc-100k"

    @pytest.mark.asyncio
    async def test_trade_message_dispatches_by_slug(self, client):
        """Trade routes to callback matched by market slug"""
        callback = Mock(return_value=None)
        trade_msg = self._make_trade_message(event_slug="no-match", slug="will-btc-hit-100k")

        import websockets.exceptions

        async def aiter_messages():
            yield trade_msg
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_messages()
        client.ws_connection = mock_ws
        client.subscriptions = {"will-btc-hit-100k": callback}

        await client.listen_for_trades(max_reconnects=0)
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_trade_dispatches_to_all_callback(self, client):
        """Trade routes to _all callback when no slug match"""
        callback = Mock(return_value=None)
        trade_msg = self._make_trade_message(event_slug="unmatched", slug="unmatched")

        import websockets.exceptions

        async def aiter_messages():
            yield trade_msg
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_messages()
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": callback}

        await client.listen_for_trades(max_reconnects=0)
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_messages_skipped(self, client):
        """Empty and whitespace messages are skipped"""
        callback = Mock(return_value=None)

        import websockets.exceptions

        async def aiter_messages():
            yield ""
            yield "   "
            yield self._make_trade_message()
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_messages()
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        await client.listen_for_trades(max_reconnects=0)
        # Only the valid trade message should trigger callback
        assert callback.call_count == 1

    @pytest.mark.asyncio
    async def test_json_decode_errors_skipped(self, client):
        """Invalid JSON messages are silently skipped"""
        callback = Mock(return_value=None)

        import websockets.exceptions

        async def aiter_messages():
            yield "not-json{{"
            yield self._make_trade_message()
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_messages()
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        await client.listen_for_trades(max_reconnects=0)
        assert callback.call_count == 1

    @pytest.mark.asyncio
    async def test_messages_without_payload_skipped(self, client):
        """Messages without payload key are skipped"""
        callback = Mock(return_value=None)

        import websockets.exceptions

        async def aiter_messages():
            yield json.dumps({"topic": "system", "type": "status"})
            yield self._make_trade_message()
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_messages()
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        await client.listen_for_trades(max_reconnects=0)
        assert callback.call_count == 1

    @pytest.mark.asyncio
    async def test_async_callback_support(self, client):
        """Async callbacks are awaited correctly"""
        calls = []

        async def async_callback(data):
            calls.append(data)

        trade_msg = self._make_trade_message()

        import websockets.exceptions

        async def aiter_messages():
            yield trade_msg
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_messages()
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": async_callback}

        await client.listen_for_trades(max_reconnects=0)
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_reconnect_attempts_reset_on_successful_message(self, client):
        """Reconnect counter resets to 0 on each successful message"""
        callback = Mock(return_value=None)

        import websockets.exceptions

        async def aiter_messages():
            yield self._make_trade_message()
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_messages()
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        # With max_reconnects=0, after ConnectionClosed it should exit
        await client.listen_for_trades(max_reconnects=0)
        callback.assert_called_once()


class TestCLOBRTDSReconnection:
    """Tests for RTDS reconnection with exponential backoff"""

    @pytest.fixture
    def client(self):
        return CLOBClient()

    @pytest.mark.asyncio
    async def test_max_reconnects_exhausted_clears_subscriptions(self, client):
        """When max_reconnects exhausted, subscriptions are cleared"""
        import websockets.exceptions

        mock_ws = AsyncMock()

        async def aiter_close():
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws.__aiter__ = lambda self: aiter_close()
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": Mock()}

        await client.listen_for_trades(max_reconnects=0)
        assert len(client.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_reconnect_on_connection_closed(self, client):
        """ConnectionClosed triggers reconnection attempt"""
        import websockets.exceptions

        call_count = 0

        async def aiter_close():
            raise websockets.exceptions.ConnectionClosed(None, None)

        async def mock_connect():
            nonlocal call_count
            call_count += 1
            mock_ws = AsyncMock()
            mock_ws.__aiter__ = lambda self: aiter_close()
            client.ws_connection = mock_ws
            return True

        # First connection fails immediately
        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_close()
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        with patch.object(client, "connect_websocket", side_effect=mock_connect):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_for_trades(max_reconnects=2)

        # Should have attempted reconnects
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_reconnect_exponential_backoff(self, client):
        """Reconnection uses exponential backoff timing"""
        import websockets.exceptions

        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        async def always_fail():
            raise Exception("connect failed")

        # Start with no connection, force reconnection path
        mock_ws = AsyncMock()

        async def aiter_close():
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws.__aiter__ = lambda self: aiter_close()
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        with patch.object(client, "connect_websocket", side_effect=always_fail):
            with patch("asyncio.sleep", side_effect=mock_sleep):
                await client.listen_for_trades(max_reconnects=3)

        # Backoff values should be exponential: 2, 4, 8 (min(2^n, 30))
        for i, wait in enumerate(sleep_calls):
            expected = min(2 ** (i + 1), 30)
            assert wait == expected, f"Backoff at attempt {i+1}: expected {expected}, got {wait}"

    @pytest.mark.asyncio
    async def test_reconnect_resubscribes(self, client):
        """After reconnect, re-subscribes to trades"""
        import websockets.exceptions

        reconnect_ws = AsyncMock()
        sent_messages = []

        async def capture_send(msg):
            sent_messages.append(json.loads(msg))

        reconnect_ws.send = capture_send

        async def aiter_close():
            raise websockets.exceptions.ConnectionClosed(None, None)

        reconnect_ws.__aiter__ = lambda self: aiter_close()

        # First WS fails
        first_ws = AsyncMock()
        first_ws.__aiter__ = lambda self: aiter_close()
        client.ws_connection = first_ws
        client.subscriptions = {"btc-100k": Mock()}

        async def mock_connect():
            client.ws_connection = reconnect_ws
            return True

        with patch.object(client, "connect_websocket", side_effect=mock_connect):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_for_trades(max_reconnects=1)

        # Verify re-subscription was sent
        assert any(
            m.get("action") == "subscribe" for m in sent_messages
        ), "Should re-subscribe after reconnect"

    @pytest.mark.asyncio
    async def test_no_connection_no_reconnect_raises(self, client):
        """If ws_connection is None on first attempt, raises"""
        client.ws_connection = None
        client.subscriptions = {}

        with pytest.raises(Exception, match="WebSocket not connected"):
            await client.listen_for_trades(max_reconnects=0)

    @pytest.mark.asyncio
    async def test_generic_exception_triggers_reconnect(self, client):
        """Non-ConnectionClosed exceptions also trigger reconnect"""
        async def aiter_error():
            raise RuntimeError("unexpected")

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: aiter_error()
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        # With max_reconnects=0, should exit after first failure
        await client.listen_for_trades(max_reconnects=0)
        assert len(client.subscriptions) == 0


class TestCLOBRTDSCloseWebSocket:
    """Tests for WebSocket cleanup"""

    @pytest.mark.asyncio
    async def test_close_websocket_closes_rtds(self):
        """close_websocket closes RTDS connection"""
        client = CLOBClient()
        mock_ws = AsyncMock()
        client.ws_connection = mock_ws

        await client.close_websocket()
        mock_ws.close.assert_awaited_once()
        assert client.ws_connection is None

    @pytest.mark.asyncio
    async def test_close_websocket_closes_clob_ws(self):
        """close_websocket closes CLOB order book connection"""
        client = CLOBClient()
        mock_clob_ws = AsyncMock()
        client.clob_ws = mock_clob_ws

        await client.close_websocket()
        mock_clob_ws.close.assert_awaited_once()
        assert client.clob_ws is None

    @pytest.mark.asyncio
    async def test_close_websocket_handles_errors_gracefully(self):
        """close_websocket swallows errors during close"""
        client = CLOBClient()
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock(side_effect=Exception("already closed"))
        client.ws_connection = mock_ws

        # Should not raise
        await client.close_websocket()
        assert client.ws_connection is None

    @pytest.mark.asyncio
    async def test_close_websocket_noop_when_not_connected(self):
        """close_websocket is safe to call when not connected"""
        client = CLOBClient()
        client.ws_connection = None
        client.clob_ws = None

        # Should not raise
        await client.close_websocket()
