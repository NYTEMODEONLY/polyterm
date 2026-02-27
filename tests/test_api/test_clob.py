"""Comprehensive tests for CLOB API client"""

import pytest
import responses
import requests
from unittest.mock import patch, MagicMock, AsyncMock
from polyterm.api.clob import CLOBClient


CLOB_ENDPOINT = "https://clob.polymarket.com"


class TestCLOBClientRequest:
    """Test _request method retry logic and error handling"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_retries_on_429(self, mock_sleep, client):
        """Test that _request retries on HTTP 429 with exponential backoff"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=429,
            headers={},
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=429,
            headers={},
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        assert len(responses.calls) == 3
        # Verify sleep was called for the two 429 retries
        assert mock_sleep.call_count == 2

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_header_valid_int(self, mock_sleep, client):
        """Test that Retry-After header (valid int) is respected on 429"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=429,
            headers={"Retry-After": "5"},
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)
        assert resp.status_code == 200
        # First sleep should use Retry-After value (min(5, 60) = 5)
        mock_sleep.assert_any_call(5)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_header_invalid_string(self, mock_sleep, client):
        """Test that invalid Retry-After header falls back to exponential backoff"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=429,
            headers={"Retry-After": "not-a-number"},
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)
        assert resp.status_code == 200
        # Should fall back to exponential backoff: min(2^0 * 2, 30) = 2
        mock_sleep.assert_any_call(2)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_capped_at_60(self, mock_sleep, client):
        """Test that Retry-After value is capped at 60 seconds"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=429,
            headers={"Retry-After": "120"},
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)
        assert resp.status_code == 200
        # Should be capped at 60
        mock_sleep.assert_any_call(60)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_retries_on_500(self, mock_sleep, client):
        """Test that _request retries on HTTP 500 server errors"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)
        assert resp.status_code == 200
        assert len(responses.calls) == 2
        # Should have slept with exponential backoff: 2^0 = 1
        mock_sleep.assert_called_once_with(1)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_500_on_last_retry_returns_response(self, mock_sleep, client):
        """Test that 500 on the last retry attempt returns the response (no retry)"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=500,
        )

        # With retries=3, the last attempt (attempt=2) is attempt < retries-1 == False,
        # so it returns the 500 response
        resp = client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)
        assert resp.status_code == 500

    @patch("time.sleep", return_value=None)
    def test_request_retries_on_timeout(self, mock_sleep, client):
        """Test that _request retries on Timeout and re-raises on exhaustion"""
        with patch.object(client.session, "request", side_effect=requests.exceptions.Timeout("timed out")):
            with pytest.raises(requests.exceptions.Timeout):
                client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)
        # Should have slept twice (for attempts 0 and 1), then raised on attempt 2
        assert mock_sleep.call_count == 2

    @patch("time.sleep", return_value=None)
    def test_request_retries_on_connection_error(self, mock_sleep, client):
        """Test that _request retries on ConnectionError and re-raises on exhaustion"""
        with patch.object(client.session, "request", side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(requests.exceptions.ConnectionError):
                client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)
        assert mock_sleep.call_count == 2

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_raises_after_exhausting_429_retries(self, mock_sleep, client):
        """Test that _request raises Exception after exhausting all retries on 429"""
        for _ in range(3):
            responses.add(
                responses.GET,
                f"{CLOB_ENDPOINT}/test",
                status=429,
            )

        with pytest.raises(Exception, match="API request failed after 3 retries"):
            client._request("GET", f"{CLOB_ENDPOINT}/test", retries=3)

    @responses.activate
    def test_request_success_first_try(self, client):
        """Test that _request returns immediately on success"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            json={"data": "value"},
            status=200,
        )

        resp = client._request("GET", f"{CLOB_ENDPOINT}/test")
        assert resp.status_code == 200
        assert resp.json() == {"data": "value"}
        assert len(responses.calls) == 1

    @responses.activate
    def test_request_returns_4xx_without_retry(self, client):
        """Test that non-429 4xx errors are returned without retry"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/test",
            status=404,
        )

        resp = client._request("GET", f"{CLOB_ENDPOINT}/test")
        assert resp.status_code == 404
        assert len(responses.calls) == 1


class TestCLOBGetOrderBook:
    """Test get_order_book method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    @responses.activate
    def test_get_order_book_success(self, client):
        """Test successful order book retrieval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/book",
            json={
                "bids": [
                    {"price": "0.65", "size": "1000"},
                    {"price": "0.64", "size": "2000"},
                    {"price": "0.63", "size": "3000"},
                ],
                "asks": [
                    {"price": "0.66", "size": "1500"},
                    {"price": "0.67", "size": "2500"},
                    {"price": "0.68", "size": "3500"},
                ],
            },
            status=200,
        )

        order_book = client.get_order_book("token123", depth=20)
        assert len(order_book["bids"]) == 3
        assert len(order_book["asks"]) == 3
        assert order_book["bids"][0]["price"] == "0.65"
        # Verify token_id was passed as a query parameter
        assert "token_id=token123" in responses.calls[0].request.url

    @responses.activate
    def test_get_order_book_depth_limiting(self, client):
        """Test that depth parameter limits the number of levels returned"""
        bids = [{"price": str(0.65 - i * 0.01), "size": "1000"} for i in range(10)]
        asks = [{"price": str(0.66 + i * 0.01), "size": "1000"} for i in range(10)]

        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/book",
            json={"bids": bids, "asks": asks},
            status=200,
        )

        order_book = client.get_order_book("token123", depth=3)
        assert len(order_book["bids"]) == 3
        assert len(order_book["asks"]) == 3

    @responses.activate
    def test_get_order_book_request_exception(self, client):
        """Test that RequestException is wrapped into a generic Exception"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/book",
            body=requests.exceptions.ConnectionError("connection failed"),
        )

        with pytest.raises(Exception, match="Failed to get order book"):
            client.get_order_book("token123")

    @responses.activate
    def test_get_order_book_empty_book(self, client):
        """Test order book with no bids or asks"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/book",
            json={"bids": [], "asks": []},
            status=200,
        )

        order_book = client.get_order_book("token123")
        assert order_book["bids"] == []
        assert order_book["asks"] == []


class TestCLOBGetTicker:
    """Test get_ticker method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    @responses.activate
    def test_get_ticker_success(self, client):
        """Test successful ticker retrieval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/ticker/market123",
            json={
                "last": "0.65",
                "volume_24h": "50000",
                "high_24h": "0.70",
                "low_24h": "0.60",
            },
            status=200,
        )

        ticker = client.get_ticker("market123")
        assert ticker["last"] == "0.65"
        assert ticker["volume_24h"] == "50000"
        assert ticker["high_24h"] == "0.70"

    @responses.activate
    def test_get_ticker_uses_request_with_retry(self, client):
        """Test that get_ticker uses _request (which has retry logic)"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/ticker/market123",
            json={"error": "server error"},
            status=500,
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/ticker/market123",
            json={"last": "0.70"},
            status=200,
        )

        with patch("time.sleep", return_value=None):
            ticker = client.get_ticker("market123")
        assert ticker["last"] == "0.70"
        assert len(responses.calls) == 2


class TestCLOBGetRecentTrades:
    """Test get_recent_trades method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    @responses.activate
    def test_get_recent_trades_success(self, client):
        """Test successful trades retrieval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/trades/market123",
            json=[
                {"id": "1", "price": "0.65", "size": "100", "side": "buy"},
                {"id": "2", "price": "0.64", "size": "200", "side": "sell"},
            ],
            status=200,
        )

        trades = client.get_recent_trades("market123", limit=100)
        assert len(trades) == 2
        assert trades[0]["price"] == "0.65"
        assert trades[1]["side"] == "sell"
        # Verify limit param was passed
        assert "limit=100" in responses.calls[0].request.url

    @responses.activate
    def test_get_recent_trades_request_exception(self, client):
        """Test that exception is wrapped properly"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/trades/market123",
            body=requests.exceptions.ConnectionError("failed"),
        )

        with pytest.raises(Exception, match="Failed to get trades"):
            client.get_recent_trades("market123")


class TestCLOBGetMarketDepth:
    """Test get_market_depth method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    @responses.activate
    def test_get_market_depth_success(self, client):
        """Test successful market depth retrieval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/depth/market123",
            json={
                "bid_depth": 10000,
                "ask_depth": 12000,
                "total_depth": 22000,
            },
            status=200,
        )

        depth = client.get_market_depth("market123")
        assert depth["bid_depth"] == 10000
        assert depth["total_depth"] == 22000

    @responses.activate
    def test_get_market_depth_uses_request_with_retry(self, client):
        """Test that get_market_depth uses _request (was recently fixed from session.get)"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/depth/market123",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/depth/market123",
            json={"bid_depth": 5000},
            status=200,
        )

        with patch("time.sleep", return_value=None):
            depth = client.get_market_depth("market123")
        assert depth["bid_depth"] == 5000
        assert len(responses.calls) == 2

    @responses.activate
    def test_get_market_depth_request_exception(self, client):
        """Test that market depth wraps exceptions"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/depth/market123",
            body=requests.exceptions.ConnectionError("failed"),
        )

        with pytest.raises(Exception, match="Failed to get market depth"):
            client.get_market_depth("market123")


class TestCLOBGetCurrentMarkets:
    """Test get_current_markets method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    @responses.activate
    def test_get_current_markets_success(self, client):
        """Test successful current markets retrieval with data key extraction"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/sampling-markets",
            json={
                "data": [
                    {"id": "1", "question": "Market 1"},
                    {"id": "2", "question": "Market 2"},
                ],
                "next_cursor": "abc123",
            },
            status=200,
        )

        markets = client.get_current_markets(limit=50)
        assert len(markets) == 2
        assert markets[0]["id"] == "1"
        # Verify limit param
        assert "limit=50" in responses.calls[0].request.url

    @responses.activate
    def test_get_current_markets_returns_data_key(self, client):
        """Test that get_current_markets extracts the 'data' key from response"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/sampling-markets",
            json={"data": [{"id": "x"}], "meta": "ignored"},
            status=200,
        )

        markets = client.get_current_markets()
        assert markets == [{"id": "x"}]

    @responses.activate
    def test_get_current_markets_empty_data(self, client):
        """Test that missing 'data' key returns empty list"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/sampling-markets",
            json={"other_key": "value"},
            status=200,
        )

        markets = client.get_current_markets()
        assert markets == []

    @responses.activate
    def test_get_current_markets_uses_request_with_retry(self, client):
        """Test that get_current_markets uses _request (was recently fixed from session.get)"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/sampling-markets",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/sampling-markets",
            json={"data": [{"id": "1"}]},
            status=200,
        )

        with patch("time.sleep", return_value=None):
            markets = client.get_current_markets()
        assert len(markets) == 1
        assert len(responses.calls) == 2

    @responses.activate
    def test_get_current_markets_request_exception(self, client):
        """Test exception wrapping"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/sampling-markets",
            body=requests.exceptions.ConnectionError("failed"),
        )

        with pytest.raises(Exception, match="Failed to get current markets"):
            client.get_current_markets()


class TestCLOBCalculateSpread:
    """Test calculate_spread utility method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    def test_calculate_spread_dict_format(self, client):
        """Test spread calculation with dict format order book"""
        order_book = {
            "bids": [{"price": "0.64", "size": "1000"}],
            "asks": [{"price": "0.66", "size": "1000"}],
        }

        spread = client.calculate_spread(order_book)
        expected = ((0.66 - 0.64) / 0.64) * 100
        assert abs(spread - expected) < 0.001

    def test_calculate_spread_list_format(self, client):
        """Test spread calculation with list format [price, size]"""
        order_book = {
            "bids": [["0.64", "1000"]],
            "asks": [["0.66", "1000"]],
        }

        spread = client.calculate_spread(order_book)
        expected = ((0.66 - 0.64) / 0.64) * 100
        assert abs(spread - expected) < 0.001

    def test_calculate_spread_empty_bids(self, client):
        """Test spread with empty bids returns 0"""
        order_book = {
            "bids": [],
            "asks": [{"price": "0.66", "size": "1000"}],
        }

        spread = client.calculate_spread(order_book)
        assert spread == 0.0

    def test_calculate_spread_empty_asks(self, client):
        """Test spread with empty asks returns 0"""
        order_book = {
            "bids": [{"price": "0.64", "size": "1000"}],
            "asks": [],
        }

        spread = client.calculate_spread(order_book)
        assert spread == 0.0

    def test_calculate_spread_no_bids_key(self, client):
        """Test spread with missing bids key returns 0"""
        spread = client.calculate_spread({"asks": [{"price": "0.66", "size": "1000"}]})
        assert spread == 0.0

    def test_calculate_spread_zero_bid(self, client):
        """Test spread with zero bid price returns 0 (avoids division by zero)"""
        order_book = {
            "bids": [{"price": "0", "size": "1000"}],
            "asks": [{"price": "0.66", "size": "1000"}],
        }

        spread = client.calculate_spread(order_book)
        assert spread == 0.0

    def test_calculate_spread_tight_market(self, client):
        """Test spread calculation for a tight market"""
        order_book = {
            "bids": [{"price": "0.50", "size": "5000"}],
            "asks": [{"price": "0.51", "size": "5000"}],
        }

        spread = client.calculate_spread(order_book)
        expected = ((0.51 - 0.50) / 0.50) * 100
        assert abs(spread - expected) < 0.001


class TestCLOBIsMarketCurrent:
    """Test is_market_current method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    def test_closed_market_returns_false(self, client):
        """Test that a closed market returns False"""
        market = {"closed": True, "end_date_iso": "2030-12-31T00:00:00Z"}
        assert client.is_market_current(market) is False

    def test_expired_market_returns_false(self, client):
        """Test that a market with a past end date returns False"""
        market = {"closed": False, "end_date_iso": "2020-01-01T00:00:00Z"}
        assert client.is_market_current(market) is False

    def test_future_market_returns_true(self, client):
        """Test that a market ending in the future returns True"""
        market = {"closed": False, "end_date_iso": "2030-12-31T00:00:00Z"}
        assert client.is_market_current(market) is True

    def test_no_date_with_active_flag(self, client):
        """Test market with no date relies on active flag"""
        market_active = {"closed": False, "active": True}
        market_inactive = {"closed": False, "active": False}

        assert client.is_market_current(market_active) is True
        assert client.is_market_current(market_inactive) is False

    def test_no_date_no_active_flag(self, client):
        """Test market with no date and no active flag"""
        market = {"closed": False}
        # No end_date and no active flag, active defaults to False via .get()
        assert client.is_market_current(market) is False

    def test_end_date_alternative_key(self, client):
        """Test that end_date key is used as fallback for end_date_iso"""
        market = {"closed": False, "end_date": "2030-12-31T00:00:00Z"}
        assert client.is_market_current(market) is True

    def test_market_from_previous_year(self, client):
        """Test market from a previous year that is past returns False"""
        market = {"closed": False, "end_date_iso": "2023-06-15T00:00:00Z"}
        assert client.is_market_current(market) is False

    def test_invalid_date_returns_false(self, client):
        """Test that invalid date format returns False gracefully"""
        market = {"closed": False, "end_date_iso": "not-a-date"}
        assert client.is_market_current(market) is False


class TestCLOBDetectLargeTrade:
    """Test detect_large_trade method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    def test_above_threshold(self, client):
        """Test that trade above threshold is detected as large"""
        trade = {"size": "20000", "price": "0.65"}
        # notional = 20000 * 0.65 = 13000
        assert client.detect_large_trade(trade, threshold=10000) is True

    def test_below_threshold(self, client):
        """Test that trade below threshold is not detected as large"""
        trade = {"size": "100", "price": "0.65"}
        # notional = 100 * 0.65 = 65
        assert client.detect_large_trade(trade, threshold=10000) is False

    def test_exactly_at_threshold(self, client):
        """Test that trade exactly at threshold is detected as large"""
        trade = {"size": "10000", "price": "1.00"}
        # notional = 10000 * 1.0 = 10000
        assert client.detect_large_trade(trade, threshold=10000) is True

    def test_default_threshold(self, client):
        """Test with default threshold of 10000"""
        large = {"size": "20000", "price": "0.75"}
        # notional = 20000 * 0.75 = 15000
        assert client.detect_large_trade(large) is True

        small = {"size": "100", "price": "0.50"}
        # notional = 100 * 0.50 = 50
        assert client.detect_large_trade(small) is False

    def test_missing_size_defaults_to_zero(self, client):
        """Test that missing size defaults to 0"""
        trade = {"price": "0.65"}
        assert client.detect_large_trade(trade) is False

    def test_missing_price_defaults_to_zero(self, client):
        """Test that missing price defaults to 0"""
        trade = {"size": "100000"}
        assert client.detect_large_trade(trade) is False


class TestCLOBClientInit:
    """Test CLOBClient initialization"""

    def test_default_endpoints(self):
        """Test default endpoint values"""
        client = CLOBClient()
        assert client.rest_endpoint == "https://clob.polymarket.com"
        assert client.ws_endpoint == "wss://ws-live-data.polymarket.com"

    def test_custom_endpoints(self):
        """Test custom endpoint values"""
        client = CLOBClient(
            rest_endpoint="https://custom.example.com/",
            ws_endpoint="wss://custom-ws.example.com",
        )
        assert client.rest_endpoint == "https://custom.example.com"
        assert client.ws_endpoint == "wss://custom-ws.example.com"

    def test_trailing_slash_stripped(self):
        """Test that trailing slash is stripped from rest endpoint"""
        client = CLOBClient(rest_endpoint="https://example.com/")
        assert client.rest_endpoint == "https://example.com"

    def test_session_created(self):
        """Test that a requests.Session is created"""
        client = CLOBClient()
        assert isinstance(client.session, requests.Session)

    def test_close_session(self):
        """Test that close() closes the session"""
        client = CLOBClient()
        with patch.object(client.session, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()

    def test_close_runs_websocket_teardown_when_connections_exist(self):
        """close() should trigger async websocket teardown when sockets are active."""
        client = CLOBClient()
        client.ws_connection = object()
        client.clob_ws = object()

        with (
            patch.object(client.session, "close") as mock_session_close,
            patch("polyterm.api.clob.asyncio.get_running_loop", side_effect=RuntimeError),
            patch(
                "polyterm.api.clob.asyncio.run",
                side_effect=lambda coroutine: coroutine.close(),
            ) as mock_asyncio_run,
        ):
            client.close()

        mock_session_close.assert_called_once()
        mock_asyncio_run.assert_called_once()


class TestCLOBGetPriceHistory:
    """Test get_price_history method"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    @responses.activate
    def test_get_price_history_success(self, client):
        """Test successful price history retrieval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={
                "history": [
                    {"t": 1704067200, "p": "0.65"},
                    {"t": 1704070800, "p": "0.66"},
                    {"t": 1704074400, "p": "0.64"},
                ]
            },
            status=200,
        )

        history = client.get_price_history("token123", interval="1h", fidelity=60)
        assert len(history) == 3
        assert history[0]["t"] == 1704067200
        assert history[0]["p"] == "0.65"
        assert history[2]["p"] == "0.64"
        # Verify query parameters
        assert "market=token123" in responses.calls[0].request.url
        assert "interval=1h" in responses.calls[0].request.url
        assert "fidelity=60" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_interval_1h(self, client):
        """Test price history with 1h interval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.50"}]},
            status=200,
        )

        history = client.get_price_history("token123", interval="1h")
        assert len(history) == 1
        assert "interval=1h" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_interval_6h(self, client):
        """Test price history with 6h interval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.75"}]},
            status=200,
        )

        history = client.get_price_history("token123", interval="6h")
        assert "interval=6h" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_interval_1d(self, client):
        """Test price history with 1d interval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.80"}]},
            status=200,
        )

        history = client.get_price_history("token123", interval="1d")
        assert "interval=1d" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_interval_max(self, client):
        """Test price history with max interval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.55"}]},
            status=200,
        )

        history = client.get_price_history("token123", interval="max")
        assert "interval=max" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_interval_1m(self, client):
        """Test price history with 1m interval"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.60"}]},
            status=200,
        )

        history = client.get_price_history("token123", interval="1m")
        assert "interval=1m" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_custom_fidelity(self, client):
        """Test price history with custom fidelity values"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.70"}]},
            status=200,
        )

        # Test fidelity=300 (5 minutes)
        history = client.get_price_history("token123", fidelity=300)
        assert "fidelity=300" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_with_start_ts(self, client):
        """Test price history with start_ts parameter"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.65"}]},
            status=200,
        )

        history = client.get_price_history("token123", start_ts=1704000000)
        assert "startTs=1704000000" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_with_end_ts(self, client):
        """Test price history with end_ts parameter"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.65"}]},
            status=200,
        )

        history = client.get_price_history("token123", end_ts=1704100000)
        assert "endTs=1704100000" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_with_start_and_end_ts(self, client):
        """Test price history with both start_ts and end_ts parameters"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.65"}]},
            status=200,
        )

        history = client.get_price_history("token123", start_ts=1704000000, end_ts=1704100000)
        assert "startTs=1704000000" in responses.calls[0].request.url
        assert "endTs=1704100000" in responses.calls[0].request.url

    @responses.activate
    def test_get_price_history_empty_history(self, client):
        """Test price history with empty history response"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": []},
            status=200,
        )

        history = client.get_price_history("token123")
        assert history == []

    @responses.activate
    def test_get_price_history_missing_history_key(self, client):
        """Test that missing 'history' key returns empty list"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"other_key": "value"},
            status=200,
        )

        history = client.get_price_history("token123")
        assert history == []

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_get_price_history_retries_on_500(self, mock_sleep, client):
        """Test that get_price_history retries on HTTP 500 and succeeds"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.65"}]},
            status=200,
        )

        history = client.get_price_history("token123")
        assert len(history) == 1
        assert history[0]["p"] == "0.65"
        assert len(responses.calls) == 2
        mock_sleep.assert_called_once_with(1)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_get_price_history_retries_on_429(self, mock_sleep, client):
        """Test that get_price_history retries on HTTP 429 with backoff"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            status=429,
            headers={},
        )
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": [{"t": 1704067200, "p": "0.65"}]},
            status=200,
        )

        history = client.get_price_history("token123")
        assert len(history) == 1
        assert len(responses.calls) == 2
        # Should sleep with exponential backoff: min(2^0 * 2, 30) = 2
        mock_sleep.assert_called_once_with(2)

    @responses.activate
    def test_get_price_history_connection_error_raises_exception(self, client):
        """Test that ConnectionError is wrapped and raised"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            body=requests.exceptions.ConnectionError("connection failed"),
        )

        with pytest.raises(Exception, match="Failed to get price history"):
            client.get_price_history("token123")

    @responses.activate
    def test_get_price_history_request_exception_wrapped(self, client):
        """Test that RequestException is wrapped into generic Exception"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            body=requests.exceptions.RequestException("generic error"),
        )

        with pytest.raises(Exception, match="Failed to get price history"):
            client.get_price_history("token123")

    @responses.activate
    def test_get_price_history_large_dataset(self, client):
        """Test price history with large history data (many points)"""
        # Simulate 100 data points
        large_history = [{"t": 1704067200 + i * 3600, "p": str(0.5 + i * 0.001)} for i in range(100)]
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": large_history},
            status=200,
        )

        history = client.get_price_history("token123", interval="1h", fidelity=3600)
        assert len(history) == 100
        assert history[0]["t"] == 1704067200
        assert history[99]["t"] == 1704067200 + 99 * 3600

    @responses.activate
    def test_get_price_history_string_prices(self, client):
        """Test that price values are returned as strings (API format)"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={
                "history": [
                    {"t": 1704067200, "p": "0.65432"},
                    {"t": 1704070800, "p": "0.12345"},
                ]
            },
            status=200,
        )

        history = client.get_price_history("token123")
        assert isinstance(history[0]["p"], str)
        assert history[0]["p"] == "0.65432"
        assert history[1]["p"] == "0.12345"

    @responses.activate
    def test_get_price_history_verifies_query_parameters(self, client):
        """Test that all query parameters are correctly passed to URL"""
        responses.add(
            responses.GET,
            f"{CLOB_ENDPOINT}/prices-history",
            json={"history": []},
            status=200,
        )

        client.get_price_history(
            "my_token_id",
            interval="6h",
            fidelity=300,
            start_ts=1700000000,
            end_ts=1700100000,
        )

        url = responses.calls[0].request.url
        assert "market=my_token_id" in url
        assert "interval=6h" in url
        assert "fidelity=300" in url
        assert "startTs=1700000000" in url
        assert "endTs=1700100000" in url


class TestCLOBWebSocketOrderBook:
    """Test CLOB WebSocket order book streaming functionality"""

    @pytest.fixture
    def client(self):
        return CLOBClient(rest_endpoint=CLOB_ENDPOINT)

    @pytest.mark.asyncio
    async def test_close_websocket_closes_rtds_and_orderbook_connections(self, client):
        """close_websocket should close both RTDS and orderbook sockets."""
        rtds_ws = AsyncMock()
        orderbook_ws = AsyncMock()
        client.ws_connection = rtds_ws
        client.clob_ws = orderbook_ws
        client.subscriptions = {"_all": MagicMock()}
        client._ob_callback = MagicMock()
        client._ob_token_ids = ["token1"]

        await client.close_websocket()

        rtds_ws.close.assert_awaited_once()
        orderbook_ws.close.assert_awaited_once()
        assert client.ws_connection is None
        assert client.clob_ws is None
        assert client.subscriptions == {}
        assert client._ob_callback is None
        assert client._ob_token_ids == []

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_connect_clob_websocket_success(self, mock_websockets, client):
        """Test successful connection to CLOB order book WebSocket"""
        mock_ws = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        result = await client.connect_clob_websocket()

        assert result is True
        assert client.clob_ws == mock_ws
        mock_websockets.connect.assert_called_once_with(client.CLOB_WS_ENDPOINT)

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", False)
    async def test_connect_clob_websocket_without_websockets_raises(self, client):
        """Test that connecting without websockets library raises exception"""
        with pytest.raises(Exception, match="websockets library not installed"):
            await client.connect_clob_websocket()

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_subscribe_orderbook_sends_correct_message(self, mock_websockets, client):
        """Test that subscribe_orderbook sends correct subscription message"""
        mock_ws = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)
        client.clob_ws = mock_ws

        token_ids = ["token1", "token2"]
        callback = MagicMock()

        await client.subscribe_orderbook(token_ids, callback)

        # Verify subscription message was sent
        mock_ws.send.assert_called_once()
        sent_message = mock_ws.send.call_args[0][0]
        import json
        msg_data = json.loads(sent_message)
        assert msg_data == {"assets_ids": ["token1", "token2"], "type": "market"}
        assert client._ob_callback == callback
        assert client._ob_token_ids == token_ids

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_subscribe_orderbook_auto_connects(self, mock_websockets, client):
        """Test that subscribe_orderbook auto-connects if not connected"""
        mock_ws = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        token_ids = ["token1"]
        callback = MagicMock()

        await client.subscribe_orderbook(token_ids, callback)

        # Should have called connect
        mock_websockets.connect.assert_called_once_with(client.CLOB_WS_ENDPOINT)
        assert client.clob_ws == mock_ws

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    async def test_listen_orderbook_processes_book_messages(self, client):
        """Test that listen_orderbook processes 'book' message type"""
        received_messages = []

        def callback(data):
            received_messages.append(data)

        book_message = '{"type": "book", "asset_id": "token1", "bids": [], "asks": []}'

        async def message_iterator():
            yield book_message
            # After yielding one message, raise exception to exit the listen loop
            raise Exception("Test complete")

        mock_ws = MagicMock()
        mock_ws.__aiter__ = lambda self: message_iterator()

        client.clob_ws = mock_ws
        client._ob_callback = callback

        # listen_orderbook will catch the exception and exit
        await client.listen_orderbook(max_reconnects=0)

        assert len(received_messages) == 1
        assert received_messages[0]["type"] == "book"

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    async def test_listen_orderbook_processes_last_trade_price_messages(self, client):
        """Test that listen_orderbook processes 'last_trade_price' message type"""
        received_messages = []

        def callback(data):
            received_messages.append(data)

        trade_message = '{"type": "last_trade_price", "asset_id": "token1", "price": "0.65"}'

        async def message_iterator():
            yield trade_message
            raise Exception("Test complete")

        mock_ws = MagicMock()
        mock_ws.__aiter__ = lambda self: message_iterator()

        client.clob_ws = mock_ws
        client._ob_callback = callback

        await client.listen_orderbook(max_reconnects=0)

        assert len(received_messages) == 1
        assert received_messages[0]["type"] == "last_trade_price"

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    async def test_listen_orderbook_skips_empty_messages(self, client):
        """Test that listen_orderbook skips empty messages"""
        received_messages = []

        def callback(data):
            received_messages.append(data)

        async def message_iterator():
            yield ""
            yield "   "
            yield '{"type": "book", "asset_id": "token1"}'
            raise Exception("Test complete")

        mock_ws = MagicMock()
        mock_ws.__aiter__ = lambda self: message_iterator()

        client.clob_ws = mock_ws
        client._ob_callback = callback

        await client.listen_orderbook(max_reconnects=0)

        # Should only receive the valid message
        assert len(received_messages) == 1
        assert received_messages[0]["type"] == "book"

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    async def test_listen_orderbook_handles_json_decode_errors(self, client):
        """Test that listen_orderbook handles JSON decode errors gracefully"""
        received_messages = []

        def callback(data):
            received_messages.append(data)

        async def message_iterator():
            yield "not valid json"
            yield '{"type": "book", "asset_id": "token1"}'
            raise Exception("Test complete")

        mock_ws = MagicMock()
        mock_ws.__aiter__ = lambda self: message_iterator()

        client.clob_ws = mock_ws
        client._ob_callback = callback

        await client.listen_orderbook(max_reconnects=0)

        # Should only receive the valid message
        assert len(received_messages) == 1
        assert received_messages[0]["type"] == "book"

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_listen_orderbook_reconnects_on_disconnection(self, mock_websockets, client):
        """Test that listen_orderbook sets clob_ws to None on disconnection"""
        # Start with a connection that will fail
        initial_ws = MagicMock()

        async def failing_iterator():
            raise Exception("Connection lost")
            yield

        initial_ws.__aiter__ = lambda self: failing_iterator()

        client.clob_ws = initial_ws
        client._ob_callback = MagicMock()
        client._ob_token_ids = ["token1"]

        # Mock reconnection attempts
        reconnect_mock = AsyncMock()
        reconnect_mock.send = AsyncMock()

        async def failing_reconnect_iterator():
            raise Exception("Still failing")
            yield

        reconnect_mock.__aiter__ = lambda self: failing_reconnect_iterator()

        mock_websockets.connect = AsyncMock(return_value=reconnect_mock)

        # Patch asyncio.sleep to avoid actual delay
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await client.listen_orderbook(max_reconnects=1)

        # After failure, clob_ws should have been set to None
        assert client.clob_ws is None
        # Should have attempted reconnection
        assert mock_websockets.connect.call_count == 1

    @pytest.mark.asyncio
    async def test_listen_orderbook_raises_if_not_connected(self, client):
        """Test that listen_orderbook raises if WebSocket not connected"""
        client.clob_ws = None

        with pytest.raises(Exception, match="CLOB WebSocket not connected"):
            await client.listen_orderbook(max_reconnects=0)

    def test_clob_ws_endpoint_has_correct_url(self, client):
        """Test that CLOB_WS_ENDPOINT has the correct URL"""
        assert client.CLOB_WS_ENDPOINT == "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    def test_clob_ws_initialized_to_none(self, client):
        """Test that clob_ws is initialized to None"""
        assert client.clob_ws is None

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_subscribe_stores_callback(self, mock_websockets, client):
        """Test that subscribe_orderbook stores the callback"""
        mock_ws = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)
        client.clob_ws = mock_ws

        callback = MagicMock()
        await client.subscribe_orderbook(["token1"], callback)

        assert client._ob_callback == callback

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_subscribe_stores_token_ids(self, mock_websockets, client):
        """Test that subscribe_orderbook stores the token IDs"""
        mock_ws = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)
        client.clob_ws = mock_ws

        token_ids = ["token1", "token2", "token3"]
        await client.subscribe_orderbook(token_ids, MagicMock())

        assert client._ob_token_ids == token_ids

    @pytest.mark.asyncio
    @patch("polyterm.api.clob.HAS_WEBSOCKETS", True)
    @patch("polyterm.api.clob.websockets")
    async def test_listen_handles_max_reconnects_limit(self, mock_websockets, client):
        """Test that listen_orderbook respects max_reconnects limit"""
        mock_ws = AsyncMock()
        mock_ws.__aiter__.side_effect = Exception("Connection failed")

        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        client.clob_ws = mock_ws
        client._ob_callback = MagicMock()
        client._ob_token_ids = ["token1"]

        # Patch asyncio.sleep to avoid actual delay
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await client.listen_orderbook(max_reconnects=2)

        # Should have attempted to reconnect 2 times (attempts 1 and 2)
        assert mock_websockets.connect.call_count == 2
