"""Comprehensive tests for CLOB API client"""

import pytest
import responses
import requests
from unittest.mock import patch, MagicMock
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
