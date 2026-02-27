"""Comprehensive tests for Data API client"""

import pytest
import responses
import requests
from unittest.mock import patch
from polyterm.api.data_api import DataAPIClient


BASE_URL = "https://data-api.polymarket.com"


class TestDataAPIClientRequest:
    """Test _request method retry logic and error handling"""

    @pytest.fixture
    def client(self):
        return DataAPIClient(base_url=BASE_URL)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_retries_on_429(self, mock_sleep, client):
        """Test that _request retries on HTTP 429 with exponential backoff"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=429,
            headers={},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=429,
            headers={},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", "/test", retries=3)
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        assert len(responses.calls) == 3
        assert mock_sleep.call_count == 2

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_header_valid_int(self, mock_sleep, client):
        """Test that Retry-After header (valid int) is respected on 429"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=429,
            headers={"Retry-After": "5"},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", "/test", retries=3)
        assert resp.status_code == 200
        mock_sleep.assert_any_call(5)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_header_invalid_string(self, mock_sleep, client):
        """Test that invalid Retry-After header falls back to exponential backoff"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=429,
            headers={"Retry-After": "not-a-number"},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", "/test", retries=3)
        assert resp.status_code == 200
        mock_sleep.assert_any_call(2)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_capped_at_60(self, mock_sleep, client):
        """Test that Retry-After value is capped at 60 seconds"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=429,
            headers={"Retry-After": "120"},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", "/test", retries=3)
        assert resp.status_code == 200
        mock_sleep.assert_any_call(60)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_retries_on_500(self, mock_sleep, client):
        """Test that _request retries on HTTP 500 server errors"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            json={"ok": True},
            status=200,
        )

        resp = client._request("GET", "/test", retries=3)
        assert resp.status_code == 200
        assert len(responses.calls) == 2
        mock_sleep.assert_called_once_with(1)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_500_on_last_retry_returns_response(self, mock_sleep, client):
        """Test that 500 on the last retry attempt returns the response (no retry)"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=500,
        )

        resp = client._request("GET", "/test", retries=3)
        assert resp.status_code == 500

    @patch("time.sleep", return_value=None)
    def test_request_retries_on_timeout(self, mock_sleep, client):
        """Test that _request retries on Timeout and re-raises on exhaustion"""
        with patch.object(client.session, "request", side_effect=requests.exceptions.Timeout("timed out")):
            with pytest.raises(requests.exceptions.Timeout):
                client._request("GET", "/test", retries=3)
        assert mock_sleep.call_count == 2

    @patch("time.sleep", return_value=None)
    def test_request_retries_on_connection_error(self, mock_sleep, client):
        """Test that _request retries on ConnectionError and re-raises on exhaustion"""
        with patch.object(client.session, "request", side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(requests.exceptions.ConnectionError):
                client._request("GET", "/test", retries=3)
        assert mock_sleep.call_count == 2

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_raises_after_exhausting_429_retries(self, mock_sleep, client):
        """Test that _request raises Exception after exhausting all retries on 429"""
        for _ in range(3):
            responses.add(
                responses.GET,
                f"{BASE_URL}/test",
                status=429,
            )

        with pytest.raises(Exception, match="API request failed after 3 retries"):
            client._request("GET", "/test", retries=3)

    @responses.activate
    def test_request_success_first_try(self, client):
        """Test that _request returns immediately on success"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            json={"data": "value"},
            status=200,
        )

        resp = client._request("GET", "/test")
        assert resp.status_code == 200
        assert resp.json() == {"data": "value"}
        assert len(responses.calls) == 1

    @responses.activate
    def test_request_returns_4xx_without_retry(self, client):
        """Test that non-429 4xx errors are returned without retry"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            status=404,
        )

        resp = client._request("GET", "/test")
        assert resp.status_code == 404
        assert len(responses.calls) == 1


class TestDataAPIGetPositions:
    """Test get_positions method"""

    @pytest.fixture
    def client(self):
        return DataAPIClient(base_url=BASE_URL)

    @responses.activate
    def test_get_positions_success(self, client):
        """Test successful positions retrieval"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            json=[
                {"market": "market1", "size": "100", "currentValue": "65"},
                {"market": "market2", "size": "200", "currentValue": "130"},
            ],
            status=200,
        )

        positions = client.get_positions("0xabc123", limit=100)
        assert len(positions) == 2
        assert positions[0]["market"] == "market1"
        assert "user=0xabc123" in responses.calls[0].request.url
        assert "limit=100" in responses.calls[0].request.url

    @responses.activate
    def test_get_positions_with_offset_and_sort(self, client):
        """Test positions with offset and custom sort_by"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            json=[{"market": "market1"}],
            status=200,
        )

        positions = client.get_positions("0xabc123", limit=50, offset=10, sort_by="PNL")
        assert len(positions) == 1
        assert "offset=10" in responses.calls[0].request.url
        assert "sortBy=PNL" in responses.calls[0].request.url

    @responses.activate
    def test_get_positions_empty_response(self, client):
        """Test positions with empty response"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            json=[],
            status=200,
        )

        positions = client.get_positions("0xabc123")
        assert positions == []

    @responses.activate
    def test_get_positions_request_exception(self, client):
        """Test that RequestException is raised"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            body=requests.exceptions.ConnectionError("connection failed"),
        )

        with pytest.raises(requests.exceptions.ConnectionError):
            client.get_positions("0xabc123")


class TestDataAPIGetActivity:
    """Test get_activity method"""

    @pytest.fixture
    def client(self):
        return DataAPIClient(base_url=BASE_URL)

    @responses.activate
    def test_get_activity_success(self, client):
        """Test successful activity retrieval"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/activity",
            json=[
                {"type": "trade", "market": "market1", "timestamp": 1234567890},
                {"type": "position", "market": "market2", "timestamp": 1234567900},
            ],
            status=200,
        )

        activity = client.get_activity("0xabc123", limit=100)
        assert len(activity) == 2
        assert activity[0]["type"] == "trade"
        assert "user=0xabc123" in responses.calls[0].request.url
        assert "limit=100" in responses.calls[0].request.url

    @responses.activate
    def test_get_activity_with_pagination(self, client):
        """Test activity with custom limit and offset"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/activity",
            json=[{"type": "trade"}],
            status=200,
        )

        activity = client.get_activity("0xabc123", limit=50, offset=20)
        assert len(activity) == 1
        assert "limit=50" in responses.calls[0].request.url
        assert "offset=20" in responses.calls[0].request.url

    @responses.activate
    def test_get_activity_empty(self, client):
        """Test activity with empty response"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/activity",
            json=[],
            status=200,
        )

        activity = client.get_activity("0xabc123")
        assert activity == []

    @responses.activate
    def test_get_activity_exception(self, client):
        """Test that exception is raised on request failure"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/activity",
            body=requests.exceptions.Timeout("timeout"),
        )

        with pytest.raises(requests.exceptions.Timeout):
            client.get_activity("0xabc123")


class TestDataAPIGetTrades:
    """Test get_trades method"""

    @pytest.fixture
    def client(self):
        return DataAPIClient(base_url=BASE_URL)

    @responses.activate
    def test_get_trades_success(self, client):
        """Test successful trades retrieval"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/trades",
            json=[
                {"id": "1", "price": "0.65", "size": "100", "side": "buy"},
                {"id": "2", "price": "0.64", "size": "200", "side": "sell"},
            ],
            status=200,
        )

        trades = client.get_trades("0xabc123", limit=100)
        assert len(trades) == 2
        assert trades[0]["price"] == "0.65"
        assert "user=0xabc123" in responses.calls[0].request.url
        assert "limit=100" in responses.calls[0].request.url

    @responses.activate
    def test_get_trades_with_market_filter(self, client):
        """Test trades with market filter"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/trades",
            json=[{"id": "1", "market": "market1"}],
            status=200,
        )

        trades = client.get_trades("0xabc123", limit=50, market="market1")
        assert len(trades) == 1
        assert "market=market1" in responses.calls[0].request.url

    @responses.activate
    def test_get_trades_empty(self, client):
        """Test trades with empty response"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/trades",
            json=[],
            status=200,
        )

        trades = client.get_trades("0xabc123")
        assert trades == []

    @responses.activate
    def test_get_trades_exception(self, client):
        """Test that exception is raised on request failure"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/trades",
            body=requests.exceptions.ConnectionError("failed"),
        )

        with pytest.raises(requests.exceptions.ConnectionError):
            client.get_trades("0xabc123")


class TestDataAPIGetProfitSummary:
    """Test get_profit_summary method"""

    @pytest.fixture
    def client(self):
        return DataAPIClient(base_url=BASE_URL)

    @responses.activate
    def test_get_profit_summary_success_with_positions(self, client):
        """Test successful profit summary with valid positions"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            json=[
                {"market": "m1", "pnl": "100.5", "initialValue": "500"},
                {"market": "m2", "pnl": "-50.25", "initialValue": "300"},
                {"market": "m3", "pnl": "25.75", "initialValue": "200"},
            ],
            status=200,
        )

        summary = client.get_profit_summary("0xabc123")
        assert summary["total_pnl"] == 100.5 - 50.25 + 25.75
        assert summary["total_invested"] == 500 + 300 + 200
        assert summary["position_count"] == 3
        assert len(summary["positions"]) == 3
        assert "sortBy=PNL" in responses.calls[0].request.url
        assert "limit=500" in responses.calls[0].request.url

    @responses.activate
    def test_get_profit_summary_empty_positions(self, client):
        """Test profit summary with no positions"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            json=[],
            status=200,
        )

        summary = client.get_profit_summary("0xabc123")
        assert summary["total_pnl"] == 0.0
        assert summary["total_invested"] == 0.0
        assert summary["position_count"] == 0
        assert summary["positions"] == []

    @responses.activate
    def test_get_profit_summary_non_list_response(self, client):
        """Test profit summary with non-list response (dict instead of list)"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            json={"error": "unexpected format"},
            status=200,
        )

        summary = client.get_profit_summary("0xabc123")
        assert summary["total_pnl"] == 0.0
        assert summary["total_invested"] == 0.0
        assert summary["position_count"] == 0
        assert summary["positions"] == []

    @responses.activate
    def test_get_profit_summary_pnl_aggregation_with_nulls(self, client):
        """Test profit summary handles null/missing values gracefully"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            json=[
                {"market": "m1", "pnl": "100", "initialValue": "500"},
                {"market": "m2", "pnl": None, "initialValue": "300"},
                {"market": "m3", "pnl": "50", "initialValue": None},
                {"market": "m4"},  # Missing both fields
            ],
            status=200,
        )

        summary = client.get_profit_summary("0xabc123")
        assert summary["total_pnl"] == 150.0
        assert summary["total_invested"] == 800.0
        assert summary["position_count"] == 4

    @responses.activate
    def test_get_profit_summary_invalid_numeric_values(self, client):
        """Test profit summary handles invalid numeric values"""
        responses.add(
            responses.GET,
            f"{BASE_URL}/positions",
            json=[
                {"market": "m1", "pnl": "not-a-number", "initialValue": "500"},
                {"market": "m2", "pnl": "100", "initialValue": "invalid"},
            ],
            status=200,
        )

        summary = client.get_profit_summary("0xabc123")
        # First position: pnl conversion fails on line 100, nothing added, continue
        # Second position: pnl=100 added on line 100, then initialValue fails on line 101
        # Result: partial update - only pnl from second position
        assert summary["total_pnl"] == 100.0
        assert summary["total_invested"] == 0.0
        assert summary["position_count"] == 2


class TestDataAPIClientInit:
    """Test DataAPIClient initialization"""

    def test_default_url(self):
        """Test default base URL value"""
        client = DataAPIClient()
        assert client.base_url == "https://data-api.polymarket.com"

    def test_custom_url(self):
        """Test custom base URL value"""
        client = DataAPIClient(base_url="https://custom.example.com")
        assert client.base_url == "https://custom.example.com"

    def test_trailing_slash_stripped(self):
        """Test that trailing slash is stripped from base URL"""
        client = DataAPIClient(base_url="https://example.com/")
        assert client.base_url == "https://example.com"

    def test_session_created(self):
        """Test that a requests.Session is created"""
        client = DataAPIClient()
        assert isinstance(client.session, requests.Session)

    def test_close_session(self):
        """Test that close() closes the session"""
        client = DataAPIClient()
        with patch.object(client.session, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()

    def test_base_url_class_constant(self):
        """Test that BASE_URL class constant is correct"""
        assert DataAPIClient.BASE_URL == "https://data-api.polymarket.com"

    def test_none_base_url_uses_default(self):
        """Test that passing None for base_url uses the default"""
        client = DataAPIClient(base_url=None)
        assert client.base_url == "https://data-api.polymarket.com"
