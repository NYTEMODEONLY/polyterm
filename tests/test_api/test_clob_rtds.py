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
        import websockets.exceptions
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            "PING",
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        mock_ws.send = AsyncMock()

        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        mock_ws.send.assert_awaited_with("PONG")

    @pytest.mark.asyncio
    async def test_trade_message_dispatches_to_callback(self, client):
        """Trade message routes to matching subscription callback"""
        import websockets.exceptions
        callback = Mock(return_value=None)
        trade_msg = self._make_trade_message(event_slug="btc-100k")

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            trade_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)

        callback.assert_called_once()
        call_data = callback.call_args[0][0]
        assert call_data["topic"] == "activity"
        assert call_data["payload"]["eventSlug"] == "btc-100k"

    @pytest.mark.asyncio
    async def test_trade_message_dispatches_by_slug(self, client):
        """Trade routes to callback matched by market slug"""
        import websockets.exceptions
        callback = Mock(return_value=None)
        trade_msg = self._make_trade_message(event_slug="no-match", slug="will-btc-hit-100k")

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            trade_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.ws_connection = mock_ws
        client.subscriptions = {"will-btc-hit-100k": callback}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_trade_dispatches_to_all_callback(self, client):
        """Trade routes to _all callback when no slug match"""
        import websockets.exceptions
        callback = Mock(return_value=None)
        trade_msg = self._make_trade_message(event_slug="unmatched", slug="unmatched")

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            trade_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": callback}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_messages_skipped(self, client):
        """Empty and whitespace messages are skipped"""
        import websockets.exceptions
        callback = Mock(return_value=None)

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            "",
            "   ",
            self._make_trade_message(),
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        # Only the valid trade message should trigger callback
        assert callback.call_count == 1

    @pytest.mark.asyncio
    async def test_json_decode_errors_skipped(self, client):
        """Invalid JSON messages are silently skipped"""
        import websockets.exceptions
        callback = Mock(return_value=None)

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            "not-json{{",
            self._make_trade_message(),
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        assert callback.call_count == 1

    @pytest.mark.asyncio
    async def test_messages_without_payload_skipped(self, client):
        """Messages without payload key are skipped"""
        import websockets.exceptions
        callback = Mock(return_value=None)

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            json.dumps({"topic": "system", "type": "status"}),
            self._make_trade_message(),
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        assert callback.call_count == 1

    @pytest.mark.asyncio
    async def test_async_callback_support(self, client):
        """Async callbacks are awaited correctly"""
        import websockets.exceptions
        calls = []

        async def async_callback(data):
            calls.append(data)

        trade_msg = self._make_trade_message()

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            trade_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": async_callback}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_reconnect_attempts_reset_on_successful_message(self, client):
        """Reconnect counter resets to 0 on each successful message"""
        import websockets.exceptions
        callback = Mock(return_value=None)

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            self._make_trade_message(),
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": callback}

        # With max_reconnects=0, after ConnectionClosed it should exit
        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
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
        mock_ws.recv = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        client.ws_connection = mock_ws
        client.subscriptions = {"btc-100k": Mock()}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        assert len(client.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_reconnect_on_connection_closed(self, client):
        """ConnectionClosed triggers reconnection attempt"""
        import websockets.exceptions

        call_count = 0

        async def mock_connect():
            nonlocal call_count
            call_count += 1
            mock_ws = AsyncMock()
            mock_ws.recv = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
            client.ws_connection = mock_ws
            return True

        # First connection fails immediately
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        with patch.object(client, "connect_websocket", side_effect=mock_connect):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_for_trades(max_reconnects=2, supervisor_retries=0)

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

        # Start with a connection that immediately fails
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        with patch.object(client, "connect_websocket", side_effect=always_fail):
            with patch("asyncio.sleep", side_effect=mock_sleep):
                await client.listen_for_trades(max_reconnects=3, supervisor_retries=0)

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
        reconnect_ws.recv = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))

        # First WS fails
        first_ws = AsyncMock()
        first_ws.recv = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        client.ws_connection = first_ws
        client.subscriptions = {"btc-100k": Mock()}

        async def mock_connect():
            client.ws_connection = reconnect_ws
            return True

        with patch.object(client, "connect_websocket", side_effect=mock_connect):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_for_trades(max_reconnects=1, supervisor_retries=0)

        # Verify re-subscription was sent
        assert any(
            m.get("action") == "subscribe" for m in sent_messages
        ), "Should re-subscribe after reconnect"

    @pytest.mark.asyncio
    async def test_no_connection_no_reconnect_permanently_fails(self, client):
        """If ws_connection is None on first attempt, permanently fails"""
        client.ws_connection = None
        client.subscriptions = {}

        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        assert client._ws_permanently_failed is True

    @pytest.mark.asyncio
    async def test_generic_exception_triggers_reconnect(self, client):
        """Non-ConnectionClosed exceptions also trigger reconnect"""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=RuntimeError("unexpected"))
        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        # With max_reconnects=0, should exit after first failure
        await client.listen_for_trades(max_reconnects=0, supervisor_retries=0)
        assert len(client.subscriptions) == 0


class TestCLOBRTDSMessageTimeout:
    """Tests for message timeout forcing reconnect"""

    @pytest.fixture
    def client(self):
        return CLOBClient()

    @pytest.mark.asyncio
    async def test_message_timeout_triggers_reconnect(self, client):
        """asyncio.TimeoutError from recv triggers reconnect"""
        import websockets.exceptions

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_ws.close = AsyncMock()

        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        await client.listen_for_trades(
            max_reconnects=0, message_timeout=0.01, supervisor_retries=0
        )

        # Timeout should have closed the stale connection
        mock_ws.close.assert_awaited_once()
        # Should have set permanently_failed since max_reconnects=0
        assert client._ws_permanently_failed is True

    @pytest.mark.asyncio
    async def test_message_timeout_resets_ws_connection(self, client):
        """After timeout, ws_connection is set to None for fresh reconnect"""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_ws.close = AsyncMock()

        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        await client.listen_for_trades(
            max_reconnects=0, message_timeout=0.01, supervisor_retries=0
        )

        # ws_connection should have been cleared for reconnect attempt
        assert client.ws_connection is None

    @pytest.mark.asyncio
    async def test_message_timeout_close_error_swallowed(self, client):
        """If close() fails on timeout, error is swallowed"""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_ws.close = AsyncMock(side_effect=Exception("already closed"))

        client.ws_connection = mock_ws
        client.subscriptions = {"_all": Mock()}

        # Should not raise
        await client.listen_for_trades(
            max_reconnects=0, message_timeout=0.01, supervisor_retries=0
        )
        assert client._ws_permanently_failed is True

    @pytest.mark.asyncio
    async def test_successful_message_after_timeout_resets_reconnects(self, client):
        """A successful message resets the reconnect counter even after a timeout"""
        import websockets.exceptions

        timeout_ws = AsyncMock()
        timeout_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
        timeout_ws.close = AsyncMock()

        trade_msg = json.dumps({
            "topic": "activity", "type": "trades",
            "payload": {"eventSlug": "test", "price": "0.5", "size": "10"}
        })

        recovery_ws = AsyncMock()
        recovery_ws.recv = AsyncMock(side_effect=[
            trade_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])

        client.ws_connection = timeout_ws
        callback = Mock(return_value=None)
        client.subscriptions = {"_all": callback}

        connect_count = 0

        async def mock_connect():
            nonlocal connect_count
            connect_count += 1
            client.ws_connection = recovery_ws
            return True

        with patch.object(client, "connect_websocket", side_effect=mock_connect):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_for_trades(
                    max_reconnects=2, message_timeout=0.01, supervisor_retries=0
                )

        # Should have reconnected and processed the trade
        callback.assert_called_once()


class TestCLOBRTDSSupervisor:
    """Tests for supervisor retry loop"""

    @pytest.fixture
    def client(self):
        return CLOBClient()

    @pytest.mark.asyncio
    async def test_supervisor_restarts_after_inner_exhaustion(self, client):
        """Supervisor restarts inner loop after cooldown when reconnects exhaust"""
        import websockets.exceptions

        inner_call_count = 0
        original_inner = client._listen_for_trades_inner

        async def counting_inner(max_reconnects, message_timeout):
            nonlocal inner_call_count
            inner_call_count += 1
            # Simulate inner loop exiting (reconnects exhausted)
            return

        with patch.object(client, "_listen_for_trades_inner", side_effect=counting_inner):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await client.listen_for_trades(
                    max_reconnects=3,
                    supervisor_retries=2,
                    supervisor_cooldown=10.0,
                )

        # Inner loop should run: 1 initial + 2 supervisor retries = 3 times
        assert inner_call_count == 3
        # Supervisor should sleep between retries
        assert mock_sleep.await_count == 2
        mock_sleep.assert_awaited_with(10.0)

    @pytest.mark.asyncio
    async def test_supervisor_resets_ws_connection_between_restarts(self, client):
        """Supervisor sets ws_connection to None before restarting"""
        ws_states = []

        async def capture_inner(max_reconnects, message_timeout):
            ws_states.append(client.ws_connection)
            client.ws_connection = AsyncMock()  # Simulate stale connection

        with patch.object(client, "_listen_for_trades_inner", side_effect=capture_inner):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_for_trades(
                    max_reconnects=1,
                    supervisor_retries=1,
                    supervisor_cooldown=0.01,
                )

        # After first inner exit, supervisor should reset ws_connection to None
        # So second inner call should see None
        assert ws_states[1] is None

    @pytest.mark.asyncio
    async def test_supervisor_zero_retries_exits_immediately(self, client):
        """supervisor_retries=0 means no supervisor restarts"""
        inner_call_count = 0

        async def counting_inner(max_reconnects, message_timeout):
            nonlocal inner_call_count
            inner_call_count += 1

        with patch.object(client, "_listen_for_trades_inner", side_effect=counting_inner):
            await client.listen_for_trades(
                max_reconnects=1,
                supervisor_retries=0,
            )

        # Only 1 inner call, no supervisor restarts
        assert inner_call_count == 1
        assert client._ws_permanently_failed is True

    @pytest.mark.asyncio
    async def test_supervisor_handles_inner_exception(self, client):
        """Supervisor catches exceptions from inner loop and continues"""
        call_count = 0

        async def failing_inner(max_reconnects, message_timeout):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("inner loop crashed")

        with patch.object(client, "_listen_for_trades_inner", side_effect=failing_inner):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_for_trades(
                    max_reconnects=1,
                    supervisor_retries=1,
                    supervisor_cooldown=0.01,
                )

        # Should have retried despite exception
        assert call_count == 2
        assert client._ws_permanently_failed is True


class TestCLOBRTDSOnError:
    """Tests for on_error callback"""

    @pytest.fixture
    def client(self):
        return CLOBClient()

    @pytest.mark.asyncio
    async def test_on_error_called_on_permanent_failure(self, client):
        """on_error is called when supervisor exhausts all retries"""
        errors = []

        def capture_error(exc):
            errors.append(str(exc))

        async def noop_inner(max_reconnects, message_timeout):
            return

        with patch.object(client, "_listen_for_trades_inner", side_effect=noop_inner):
            await client.listen_for_trades(
                max_reconnects=1,
                supervisor_retries=0,
                on_error=capture_error,
            )

        assert len(errors) == 1
        assert "permanently failed" in errors[0]

    @pytest.mark.asyncio
    async def test_on_error_called_on_supervisor_restart(self, client):
        """on_error is called on each supervisor restart (not just final)"""
        errors = []

        def capture_error(exc):
            errors.append(str(exc))

        async def noop_inner(max_reconnects, message_timeout):
            return

        with patch.object(client, "_listen_for_trades_inner", side_effect=noop_inner):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_for_trades(
                    max_reconnects=1,
                    supervisor_retries=2,
                    supervisor_cooldown=0.01,
                    on_error=capture_error,
                )

        # 2 supervisor restart notifications + 1 permanent failure
        assert len(errors) == 3
        assert any("supervisor restart" in e for e in errors)
        assert any("permanently failed" in e for e in errors)

    @pytest.mark.asyncio
    async def test_on_error_exception_swallowed(self, client):
        """If on_error itself raises, it's swallowed"""
        def bad_callback(exc):
            raise RuntimeError("callback crashed")

        async def noop_inner(max_reconnects, message_timeout):
            return

        with patch.object(client, "_listen_for_trades_inner", side_effect=noop_inner):
            # Should not raise
            await client.listen_for_trades(
                max_reconnects=1,
                supervisor_retries=0,
                on_error=bad_callback,
            )

        assert client._ws_permanently_failed is True

    @pytest.mark.asyncio
    async def test_permanently_failed_flag_set(self, client):
        """_ws_permanently_failed flag is set on final supervisor failure"""
        assert client._ws_permanently_failed is False

        async def noop_inner(max_reconnects, message_timeout):
            return

        with patch.object(client, "_listen_for_trades_inner", side_effect=noop_inner):
            await client.listen_for_trades(
                max_reconnects=1,
                supervisor_retries=0,
            )

        assert client._ws_permanently_failed is True

    @pytest.mark.asyncio
    async def test_subscriptions_cleared_on_permanent_failure(self, client):
        """Subscriptions are cleared when supervisor gives up"""
        client.subscriptions = {"slug-a": Mock(), "slug-b": Mock()}

        async def noop_inner(max_reconnects, message_timeout):
            return

        with patch.object(client, "_listen_for_trades_inner", side_effect=noop_inner):
            await client.listen_for_trades(
                max_reconnects=1,
                supervisor_retries=0,
            )

        assert len(client.subscriptions) == 0


class TestCLOBOrderbookWSTimeout:
    """Tests for orderbook WebSocket message timeout"""

    @pytest.fixture
    def client(self):
        c = CLOBClient()
        return c

    @pytest.mark.asyncio
    async def test_orderbook_timeout_triggers_reconnect(self, client):
        """Orderbook WS timeout closes connection and increments reconnects"""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_ws.close = AsyncMock()
        client.clob_ws = mock_ws
        client._ob_callback = Mock()
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0, message_timeout=0.01)

        mock_ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_orderbook_timeout_close_error_swallowed(self, client):
        """Orderbook timeout swallows close() errors"""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_ws.close = AsyncMock(side_effect=Exception("already closed"))
        client.clob_ws = mock_ws
        client._ob_callback = Mock()
        client._ob_token_ids = ["token1"]

        # Should not raise
        await client.listen_orderbook(max_reconnects=0, message_timeout=0.01)

    @pytest.mark.asyncio
    async def test_orderbook_processes_book_message(self, client):
        """Orderbook WS processes book-type messages via callback"""
        import websockets.exceptions

        callback = Mock(return_value=None)
        book_msg = json.dumps({"type": "book", "bids": [], "asks": []})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            book_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = callback
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)

        callback.assert_called_once()
        call_data = callback.call_args[0][0]
        assert call_data["type"] == "book"

    @pytest.mark.asyncio
    async def test_orderbook_processes_price_change_message(self, client):
        """Orderbook WS processes price_change messages"""
        import websockets.exceptions

        callback = Mock(return_value=None)
        msg = json.dumps({"type": "price_change", "price": "0.65"})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = callback
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_orderbook_processes_last_trade_price(self, client):
        """Orderbook WS processes last_trade_price messages"""
        import websockets.exceptions

        callback = Mock(return_value=None)
        msg = json.dumps({"type": "last_trade_price", "price": "0.70"})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = callback
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_orderbook_skips_empty_messages(self, client):
        """Orderbook WS skips empty/whitespace messages"""
        import websockets.exceptions

        callback = Mock(return_value=None)
        book_msg = json.dumps({"type": "book", "bids": [], "asks": []})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            "",
            "   ",
            book_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = callback
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)
        assert callback.call_count == 1

    @pytest.mark.asyncio
    async def test_orderbook_clears_callback_on_failure(self, client):
        """Orderbook clears _ob_callback when max_reconnects exhausted"""
        import websockets.exceptions

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        client.clob_ws = mock_ws
        client._ob_callback = Mock()
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0)
        assert client._ob_callback is None

    @pytest.mark.asyncio
    async def test_orderbook_reconnect_resubscribes(self, client):
        """Orderbook re-subscribes with token_ids after reconnect"""
        import websockets.exceptions

        sent_messages = []
        reconnect_ws = AsyncMock()

        async def capture_send(msg):
            sent_messages.append(json.loads(msg))

        reconnect_ws.send = capture_send
        reconnect_ws.recv = AsyncMock(
            side_effect=websockets.exceptions.ConnectionClosed(None, None)
        )

        first_ws = AsyncMock()
        first_ws.recv = AsyncMock(
            side_effect=websockets.exceptions.ConnectionClosed(None, None)
        )
        client.clob_ws = first_ws
        client._ob_callback = Mock()
        client._ob_token_ids = ["token-abc", "token-def"]

        async def mock_connect():
            client.clob_ws = reconnect_ws
            return True

        with patch.object(client, "connect_clob_websocket", side_effect=mock_connect):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.listen_orderbook(max_reconnects=1)

        assert any(
            m.get("assets_ids") == ["token-abc", "token-def"] for m in sent_messages
        ), "Should re-subscribe with token IDs after reconnect"


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


class TestCLOBCloseWebSocketDualCleanup:
    """Tests for close_websocket cleaning up both connections simultaneously"""

    @pytest.mark.asyncio
    async def test_close_websocket_closes_both_connections(self):
        """close_websocket closes both RTDS and CLOB WS when both are active"""
        client = CLOBClient()
        mock_rtds = AsyncMock()
        mock_clob = AsyncMock()
        client.ws_connection = mock_rtds
        client.clob_ws = mock_clob

        await client.close_websocket()

        mock_rtds.close.assert_awaited_once()
        mock_clob.close.assert_awaited_once()
        assert client.ws_connection is None
        assert client.clob_ws is None

    @pytest.mark.asyncio
    async def test_close_websocket_clears_subscriptions_and_ob_state(self):
        """close_websocket clears subscriptions, _ob_callback, and _ob_token_ids"""
        client = CLOBClient()
        client.ws_connection = AsyncMock()
        client.clob_ws = AsyncMock()
        client.subscriptions = {"slug-a": Mock(), "_all": Mock()}
        client._ob_callback = Mock()
        client._ob_token_ids = ["token-1", "token-2"]

        await client.close_websocket()

        assert len(client.subscriptions) == 0
        assert client._ob_callback is None
        assert client._ob_token_ids == []

    @pytest.mark.asyncio
    async def test_close_websocket_rtds_error_still_closes_clob(self):
        """If RTDS close() throws, CLOB WS is still closed"""
        client = CLOBClient()
        mock_rtds = AsyncMock()
        mock_rtds.close = AsyncMock(side_effect=Exception("rtds close error"))
        mock_clob = AsyncMock()
        client.ws_connection = mock_rtds
        client.clob_ws = mock_clob

        await client.close_websocket()

        mock_clob.close.assert_awaited_once()
        assert client.ws_connection is None
        assert client.clob_ws is None

    @pytest.mark.asyncio
    async def test_close_websocket_clears_ob_callback_without_clob_ws(self):
        """close_websocket clears _ob_callback even when clob_ws is None"""
        client = CLOBClient()
        client._ob_callback = Mock()
        client._ob_token_ids = ["token-x"]

        await client.close_websocket()

        assert client._ob_callback is None
        assert client._ob_token_ids == []


class TestCLOBOrderbookAsyncCallback:
    """Tests for orderbook async callback support"""

    @pytest.fixture
    def client(self):
        return CLOBClient()

    @pytest.mark.asyncio
    async def test_orderbook_async_callback_awaited(self, client):
        """Orderbook WS awaits async callbacks"""
        import websockets.exceptions

        callback = AsyncMock(return_value=None)
        msg = json.dumps({"type": "book", "bids": [], "asks": []})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = callback
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)

        callback.assert_awaited_once()
        call_data = callback.call_args[0][0]
        assert call_data["type"] == "book"

    @pytest.mark.asyncio
    async def test_orderbook_callback_exception_does_not_crash(self, client):
        """Orderbook WS swallows callback exceptions and continues"""
        import websockets.exceptions

        callback = Mock(side_effect=RuntimeError("callback exploded"))
        book_msg = json.dumps({"type": "book", "bids": [], "asks": []})
        price_msg = json.dumps({"type": "price_change", "price": "0.5"})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            book_msg,
            price_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = callback
        client._ob_token_ids = ["token1"]

        # Should not raise despite callback errors
        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)

        # Both messages should have triggered callback attempts
        assert callback.call_count == 2

    @pytest.mark.asyncio
    async def test_orderbook_ignores_unknown_message_types(self, client):
        """Orderbook WS ignores messages with unrecognized types"""
        import websockets.exceptions

        callback = Mock(return_value=None)
        unknown_msg = json.dumps({"type": "heartbeat", "ts": 1234})
        book_msg = json.dumps({"type": "book", "bids": [], "asks": []})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            unknown_msg,
            book_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = callback
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)

        # Only book message should trigger callback
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_orderbook_json_decode_error_skipped(self, client):
        """Orderbook WS skips malformed JSON and continues"""
        import websockets.exceptions

        callback = Mock(return_value=None)
        book_msg = json.dumps({"type": "book", "bids": [], "asks": []})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            "not valid json{{{",
            book_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = callback
        client._ob_token_ids = ["token1"]

        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_orderbook_no_callback_skips_processing(self, client):
        """Orderbook WS skips callback invocation when _ob_callback is None"""
        import websockets.exceptions

        book_msg = json.dumps({"type": "book", "bids": [], "asks": []})

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            book_msg,
            websockets.exceptions.ConnectionClosed(None, None),
        ])
        client.clob_ws = mock_ws
        client._ob_callback = None
        client._ob_token_ids = ["token1"]

        # Should not raise
        await client.listen_orderbook(max_reconnects=0, message_timeout=5.0)


class TestCLOBSyncClose:
    """Tests for synchronous close() method"""

    def test_close_noop_when_no_websockets(self):
        """close() only closes REST session when no WS connections exist"""
        client = CLOBClient()
        client.ws_connection = None
        client.clob_ws = None
        client.session = Mock()

        client.close()

        client.session.close.assert_called_once()

    def test_close_schedules_ws_cleanup_on_running_loop(self):
        """close() schedules close_websocket when event loop is running"""
        client = CLOBClient()
        client.ws_connection = AsyncMock()
        client.session = Mock()

        mock_loop = Mock()
        mock_loop.is_running.return_value = True

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            client.close()

        client.session.close.assert_called_once()
        mock_loop.create_task.assert_called_once()

    def test_close_runs_ws_cleanup_without_running_loop(self):
        """close() runs close_websocket synchronously when no loop running"""
        client = CLOBClient()
        client.ws_connection = AsyncMock()
        client.session = Mock()

        with patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")):
            with patch("asyncio.run") as mock_run:
                client.close()

        client.session.close.assert_called_once()
        mock_run.assert_called_once()


class TestCLOBSubscribeEdgeCases:
    """Tests for subscribe method edge cases"""

    @pytest.fixture
    def client(self):
        return CLOBClient()

    @pytest.mark.asyncio
    async def test_subscribe_auto_connects_if_clob_ws_missing(self, client):
        """subscribe_orderbook auto-connects when clob_ws is None"""
        mock_ws = AsyncMock()
        with patch.object(client, "connect_clob_websocket") as mock_connect:
            async def set_ws():
                client.clob_ws = mock_ws
            mock_connect.side_effect = set_ws

            callback = Mock()
            await client.subscribe_orderbook(["token-1"], callback)

            mock_connect.assert_awaited_once()
            assert client._ob_callback is callback
            assert client._ob_token_ids == ["token-1"]

    @pytest.mark.asyncio
    async def test_subscribe_orderbook_sends_correct_message(self, client):
        """subscribe_orderbook sends assets_ids and type=market"""
        sent = []
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock(side_effect=lambda m: sent.append(json.loads(m)))
        client.clob_ws = mock_ws

        await client.subscribe_orderbook(["tok-a", "tok-b"], Mock())

        assert len(sent) == 1
        assert sent[0]["assets_ids"] == ["tok-a", "tok-b"]
        assert sent[0]["type"] == "market"

    @pytest.mark.asyncio
    async def test_subscribe_trades_resubscribes_with_new_slugs(self, client):
        """subscribe_to_trades can be called again with different slugs"""
        mock_ws = AsyncMock()
        client.ws_connection = mock_ws

        cb1 = Mock()
        cb2 = Mock()
        await client.subscribe_to_trades(["slug-a"], cb1)
        await client.subscribe_to_trades(["slug-b"], cb2)

        assert client.subscriptions["slug-a"] is cb1
        assert client.subscriptions["slug-b"] is cb2

    @pytest.mark.asyncio
    async def test_subscribe_trades_overwrites_same_slug_callback(self, client):
        """Subscribing to same slug again overwrites the callback"""
        mock_ws = AsyncMock()
        client.ws_connection = mock_ws

        cb1 = Mock()
        cb2 = Mock()
        await client.subscribe_to_trades(["slug-a"], cb1)
        await client.subscribe_to_trades(["slug-a"], cb2)

        assert client.subscriptions["slug-a"] is cb2


class TestCLOBRTDSInnerReconnect:
    """Tests for RTDS inner loop reconnect edge cases"""

    @pytest.fixture
    def client(self):
        return CLOBClient()

    @pytest.mark.asyncio
    async def test_inner_loop_reconnect_failure_increments_attempts(self, client):
        """Failed reconnect in inner loop increments counter and eventually exits"""
        client.ws_connection = None
        client.subscriptions = {"slug-a": Mock()}

        # First call: ws_connection is None + reconnect_attempts=0 → raises "not connected"
        with pytest.raises(Exception, match="WebSocket not connected"):
            await client._listen_for_trades_inner(max_reconnects=3, message_timeout=5.0)

    @pytest.mark.asyncio
    async def test_inner_loop_resubscribes_on_reconnect(self, client):
        """Inner loop re-sends subscribe message after reconnecting"""
        import websockets.exceptions

        sent_messages = []
        reconnect_ws = AsyncMock()
        reconnect_ws.recv = AsyncMock(
            side_effect=websockets.exceptions.ConnectionClosed(None, None)
        )

        async def capture_send(msg):
            sent_messages.append(json.loads(msg))

        reconnect_ws.send = capture_send

        # First WS drops immediately
        first_ws = AsyncMock()
        first_ws.recv = AsyncMock(
            side_effect=websockets.exceptions.ConnectionClosed(None, None)
        )
        client.ws_connection = first_ws
        client.subscriptions = {"slug-a": Mock()}

        async def mock_connect():
            client.ws_connection = reconnect_ws
            return True

        with patch.object(client, "connect_websocket", side_effect=mock_connect):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client._listen_for_trades_inner(max_reconnects=1, message_timeout=5.0)

        # Should have re-subscribed with activity/trades
        assert any(
            m.get("action") == "subscribe" for m in sent_messages
        ), "Should re-subscribe after reconnect"
