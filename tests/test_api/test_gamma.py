"""Comprehensive tests for Gamma Markets API client"""

import time
import pytest
import responses
import requests
from unittest.mock import patch, MagicMock
from polyterm.api.gamma import GammaClient, RateLimiter


GAMMA_ENDPOINT = "https://gamma-api.polymarket.com"


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_initialization(self):
        """Test rate limiter initializes with correct values"""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert limiter.min_interval == 1.0
        assert limiter.last_request_time == 0

    def test_initialization_high_rate(self):
        """Test rate limiter with high request rate"""
        limiter = RateLimiter(requests_per_minute=120)
        assert limiter.min_interval == 0.5

    def test_initialization_low_rate(self):
        """Test rate limiter with low request rate"""
        limiter = RateLimiter(requests_per_minute=30)
        assert limiter.min_interval == 2.0

    def test_first_call_no_wait(self):
        """Test that the first call does not wait (last_request_time is 0)"""
        limiter = RateLimiter(requests_per_minute=60)
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        # First call should be near-instant since last_request_time=0 is far in the past
        assert elapsed < 0.1

    def test_wait_if_needed_enforces_delay(self):
        """Test that consecutive calls enforce the minimum interval"""
        limiter = RateLimiter(requests_per_minute=120)  # 0.5s interval
        limiter.wait_if_needed()  # First call - no wait
        start = time.time()
        limiter.wait_if_needed()  # Second call - should wait
        elapsed = time.time() - start
        assert elapsed >= limiter.min_interval - 0.05  # Small tolerance

    def test_updates_last_request_time(self):
        """Test that wait_if_needed updates last_request_time"""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.last_request_time == 0
        limiter.wait_if_needed()
        assert limiter.last_request_time > 0

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_calculates_correct_sleep_duration(self, mock_time, mock_sleep):
        """Test the exact sleep duration calculation"""
        limiter = RateLimiter(requests_per_minute=60)  # 1.0s interval
        # Simulate: last request was at t=10.0, current time is t=10.3
        limiter.last_request_time = 10.0
        mock_time.side_effect = [10.3, 10.7]  # current_time, then after sleep for update

        limiter.wait_if_needed()

        # Should sleep for 1.0 - 0.3 = 0.7 seconds
        mock_sleep.assert_called_once_with(pytest.approx(0.7, abs=0.01))


class TestGammaClientRequest:
    """Test _request method retry logic and error handling"""

    @pytest.fixture
    def client(self):
        client = GammaClient(base_url=GAMMA_ENDPOINT)
        # Set last_request_time far in the past to avoid rate limiter delays in tests
        client.rate_limiter.last_request_time = 0
        return client

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_retries_on_429(self, mock_sleep, client):
        """Test that _request retries on HTTP 429"""
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", status=429, headers={})
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", json={"ok": True}, status=200)

        result = client._request("GET", "/test", retries=3)
        assert result == {"ok": True}
        assert len(responses.calls) == 2

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_valid_int(self, mock_sleep, client):
        """Test Retry-After header with valid integer on 429"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/test",
            status=429,
            headers={"Retry-After": "7"},
        )
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", json={"data": 1}, status=200)

        result = client._request("GET", "/test", retries=3)
        assert result == {"data": 1}
        # Should sleep with min(7, 60) = 7
        mock_sleep.assert_any_call(7)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_invalid_string(self, mock_sleep, client):
        """Test invalid Retry-After header falls back to exponential backoff"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/test",
            status=429,
            headers={"Retry-After": "invalid-value"},
        )
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", json={"ok": True}, status=200)

        result = client._request("GET", "/test", retries=3)
        assert result == {"ok": True}
        # Falls back to min(2^0 * 2, 30) = 2
        mock_sleep.assert_any_call(2)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_429_retry_after_capped_at_60(self, mock_sleep, client):
        """Test Retry-After is capped at 60 seconds"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/test",
            status=429,
            headers={"Retry-After": "200"},
        )
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", json={}, status=200)

        client._request("GET", "/test", retries=3)
        mock_sleep.assert_any_call(60)

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_retries_on_500(self, mock_sleep, client):
        """Test that _request retries on HTTP 500 server errors"""
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", status=500)
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", json={"ok": True}, status=200)

        result = client._request("GET", "/test", retries=3)
        assert result == {"ok": True}
        assert len(responses.calls) == 2

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_raises_after_exhausting_429_retries(self, mock_sleep, client):
        """Test that exhausting all retries on 429 raises Exception"""
        for _ in range(3):
            responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", status=429)

        with pytest.raises(Exception, match="API request failed after 3 attempts"):
            client._request("GET", "/test", retries=3)

    @patch("time.sleep", return_value=None)
    def test_request_retries_on_timeout_then_raises(self, mock_sleep, client):
        """Test that Timeout is retried and then wrapped in Exception"""
        with patch.object(
            client.session, "request", side_effect=requests.exceptions.Timeout("timed out")
        ):
            with pytest.raises(Exception, match="API request timed out"):
                client._request("GET", "/test", retries=3)

    @patch("time.sleep", return_value=None)
    def test_request_retries_on_connection_error_then_raises(self, mock_sleep, client):
        """Test that ConnectionError is retried and then wrapped in Exception"""
        with patch.object(
            client.session, "request", side_effect=requests.exceptions.ConnectionError("refused")
        ):
            with pytest.raises(Exception, match="Connection failed"):
                client._request("GET", "/test", retries=3)

    @responses.activate
    def test_request_raises_on_4xx(self, client):
        """Test that non-429 4xx errors raise immediately (no retry)"""
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", status=404, json={"error": "not found"})

        with pytest.raises(Exception, match="API request failed"):
            client._request("GET", "/test")
        assert len(responses.calls) == 1

    @responses.activate
    def test_request_success_returns_json(self, client):
        """Test that successful response returns parsed JSON"""
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", json={"key": "value"}, status=200)

        result = client._request("GET", "/test")
        assert result == {"key": "value"}

    @responses.activate
    @patch("time.sleep", return_value=None)
    def test_request_500_last_attempt_raises(self, mock_sleep, client):
        """Test that 500 on every attempt results in raise_for_status on last one"""
        for _ in range(3):
            responses.add(responses.GET, f"{GAMMA_ENDPOINT}/test", status=500)

        # The last attempt (attempt=2, retries-1=2) doesn't continue, so raise_for_status is called
        with pytest.raises(Exception):
            client._request("GET", "/test", retries=3)


class TestGammaGetMarkets:
    """Test get_markets method"""

    @pytest.fixture
    def client(self):
        client = GammaClient(base_url=GAMMA_ENDPOINT)
        client.rate_limiter.last_request_time = 0
        return client

    @responses.activate
    def test_get_markets_success(self, client):
        """Test getting markets returns list"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets",
            json=[
                {"id": "1", "question": "Market A", "volume": 10000},
                {"id": "2", "question": "Market B", "volume": 20000},
            ],
            status=200,
        )

        markets = client.get_markets(limit=10)
        assert len(markets) == 2
        assert markets[0]["id"] == "1"

    @responses.activate
    def test_get_markets_params_passed_correctly(self, client):
        """Test that all parameters are passed correctly"""
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/markets", json=[], status=200)

        client.get_markets(limit=50, offset=10, active=True, closed=False, tag="crypto")

        request_url = responses.calls[0].request.url
        assert "limit=50" in request_url
        assert "offset=10" in request_url
        assert "active=true" in request_url
        assert "closed=false" in request_url
        assert "tag=crypto" in request_url

    @responses.activate
    def test_get_markets_defaults_active_true_closed_false(self, client):
        """Test that default parameters set active=true and closed=false"""
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/markets", json=[], status=200)

        client.get_markets()

        request_url = responses.calls[0].request.url
        assert "active=true" in request_url
        assert "closed=false" in request_url


class TestGammaGetMarket:
    """Test get_market method"""

    @pytest.fixture
    def client(self):
        client = GammaClient(base_url=GAMMA_ENDPOINT)
        client.rate_limiter.last_request_time = 0
        return client

    @responses.activate
    def test_get_market_success(self, client):
        """Test single market lookup"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets/abc123",
            json={"id": "abc123", "question": "Will it rain?", "volume": 5000},
            status=200,
        )

        market = client.get_market("abc123")
        assert market["id"] == "abc123"
        assert market["question"] == "Will it rain?"

    @responses.activate
    def test_get_market_not_found(self, client):
        """Test that 404 raises exception"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets/nonexistent",
            json={"error": "not found"},
            status=404,
        )

        with pytest.raises(Exception, match="API request failed"):
            client.get_market("nonexistent")


class TestGammaSearchMarkets:
    """Test search_markets method"""

    @pytest.fixture
    def client(self):
        client = GammaClient(base_url=GAMMA_ENDPOINT)
        client.rate_limiter.last_request_time = 0
        return client

    @responses.activate
    def test_search_markets_search_endpoint_success(self, client):
        """Test that search_markets uses search endpoint first"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets/search",
            json=[
                {"id": "1", "question": "Bitcoin price prediction"},
                {"id": "2", "question": "Ethereum price prediction"},
            ],
            status=200,
        )

        results = client.search_markets("bitcoin", limit=5)
        assert len(results) == 2
        assert "Bitcoin" in results[0]["question"]
        # Verify search params
        assert "q=bitcoin" in responses.calls[0].request.url
        assert "limit=5" in responses.calls[0].request.url

    @responses.activate
    def test_search_markets_fallback_to_local_filter(self, client):
        """Test that search_markets falls back to local filtering on search endpoint failure"""
        # Search endpoint fails
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets/search",
            status=500,
        )
        # Also add the 500 retry responses (retries=3 means up to 3 attempts)
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/markets/search", status=500)
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/markets/search", status=500)
        # Fallback: get_markets returns list
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets",
            json=[
                {"id": "1", "question": "Bitcoin price target"},
                {"id": "2", "question": "Ethereum staking"},
                {"id": "3", "question": "Will Bitcoin hit 100k?"},
            ],
            status=200,
        )

        with patch("time.sleep", return_value=None):
            results = client.search_markets("bitcoin", limit=5)

        assert len(results) == 2  # "Bitcoin price target" and "Will Bitcoin hit 100k?"
        for r in results:
            assert "bitcoin" in r["question"].lower()

    @responses.activate
    def test_search_markets_fallback_respects_limit(self, client):
        """Test that fallback local filter respects limit parameter"""
        # Search endpoint fails
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/markets/search", status=500)
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/markets/search", status=500)
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/markets/search", status=500)
        # Fallback returns many bitcoin markets
        markets = [{"id": str(i), "question": f"Bitcoin market {i}"} for i in range(10)]
        responses.add(responses.GET, f"{GAMMA_ENDPOINT}/markets", json=markets, status=200)

        with patch("time.sleep", return_value=None):
            results = client.search_markets("bitcoin", limit=3)

        assert len(results) == 3

    @responses.activate
    def test_search_markets_empty_search_result_triggers_fallback(self, client):
        """Test that empty search results trigger fallback"""
        # Search endpoint returns empty list (falsy)
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets/search",
            json=[],
            status=200,
        )
        # Fallback
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets",
            json=[{"id": "1", "question": "Bitcoin futures"}],
            status=200,
        )

        results = client.search_markets("bitcoin")
        assert len(results) == 1
        assert "Bitcoin" in results[0]["question"]


class TestGammaGetTrendingMarkets:
    """Test get_trending_markets method"""

    @pytest.fixture
    def client(self):
        client = GammaClient(base_url=GAMMA_ENDPOINT)
        client.rate_limiter.last_request_time = 0
        return client

    @responses.activate
    def test_get_trending_markets_correct_params(self, client):
        """Test that trending markets uses correct parameters"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets",
            json=[{"id": "1", "volume": 100000}],
            status=200,
        )

        client.get_trending_markets(limit=10)

        request_url = responses.calls[0].request.url
        assert "order=volume24hr" in request_url
        assert "ascending=false" in request_url
        assert "active=true" in request_url
        assert "closed=false" in request_url
        assert "limit=10" in request_url

    @responses.activate
    def test_get_trending_markets_returns_list(self, client):
        """Test that trending markets returns a list"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets",
            json=[
                {"id": "1", "volume": 100000},
                {"id": "2", "volume": 80000},
            ],
            status=200,
        )

        trending = client.get_trending_markets(limit=5)
        assert len(trending) == 2
        assert trending[0]["volume"] == 100000


class TestGammaIsMarketFresh:
    """Test is_market_fresh method"""

    @pytest.fixture
    def client(self):
        return GammaClient(base_url=GAMMA_ENDPOINT)

    def test_active_not_closed_returns_true(self, client):
        """Test market with active=True and closed=False is fresh"""
        market = {"active": True, "closed": False}
        assert client.is_market_fresh(market) is True

    def test_active_and_closed_returns_false(self, client):
        """Test market with active=True but closed=True is not fresh"""
        market = {"active": True, "closed": True}
        assert client.is_market_fresh(market) is False

    def test_inactive_and_not_closed_returns_false(self, client):
        """Test market with active=False and closed=False is not fresh"""
        market = {"active": False, "closed": False}
        assert client.is_market_fresh(market) is False

    def test_no_flags_with_future_end_date(self, client):
        """Test market with no active/closed flags but future end date"""
        market = {"endDate": "2030-12-31T00:00:00Z"}
        assert client.is_market_fresh(market) is True

    def test_no_flags_with_past_end_date(self, client):
        """Test market with no active/closed flags and past end date is stale"""
        market = {"endDate": "2020-01-01T00:00:00Z"}
        assert client.is_market_fresh(market) is False

    def test_no_flags_no_date_returns_false(self, client):
        """Test market with no flags and no date is considered stale"""
        market = {}
        assert client.is_market_fresh(market) is False

    def test_expired_market_outside_max_age(self, client):
        """Test market that ended more than max_age_hours ago is stale"""
        market = {"endDate": "2020-01-01T00:00:00Z"}
        assert client.is_market_fresh(market, max_age_hours=24) is False

    def test_end_date_iso_key(self, client):
        """Test that end_date_iso key is also checked"""
        market = {"end_date_iso": "2030-12-31T00:00:00Z"}
        assert client.is_market_fresh(market) is True

    def test_invalid_date_returns_false(self, client):
        """Test that invalid date format returns False"""
        market = {"endDate": "not-a-date"}
        assert client.is_market_fresh(market) is False

    def test_only_active_flag_true(self, client):
        """Test market with only active flag (no closed flag) and no date"""
        market = {"active": True}
        # active is not None, closed is None, so the primary check is skipped
        # Falls to date check, no date, then checks active flag as fallback
        assert client.is_market_fresh(market) is True

    def test_only_active_flag_false(self, client):
        """Test market with only active=False (no closed flag) and no date"""
        market = {"active": False}
        assert client.is_market_fresh(market) is False


class TestGammaFilterFreshMarkets:
    """Test filter_fresh_markets method"""

    @pytest.fixture
    def client(self):
        return GammaClient(base_url=GAMMA_ENDPOINT)

    def test_filters_out_closed_markets(self, client):
        """Test that closed markets are filtered out"""
        markets = [
            {"active": True, "closed": False, "volume": 100},
            {"active": True, "closed": True, "volume": 200},
        ]

        result = client.filter_fresh_markets(markets)
        assert len(result) == 1
        assert result[0]["volume"] == 100

    def test_filters_out_stale_markets(self, client):
        """Test that stale/inactive markets are filtered out"""
        markets = [
            {"active": True, "closed": False, "volume": 100},
            {"active": False, "closed": False, "volume": 200},
        ]

        result = client.filter_fresh_markets(markets)
        assert len(result) == 1
        assert result[0]["volume"] == 100

    def test_filters_out_low_volume(self, client):
        """Test that markets below minimum volume are filtered out"""
        markets = [
            {"active": True, "closed": False, "volume": 100, "volume24hr": 0},
            {"active": True, "closed": False, "volume": 0, "volume24hr": 0},
        ]

        result = client.filter_fresh_markets(markets, require_volume=True, min_volume=50)
        assert len(result) == 1
        assert result[0]["volume"] == 100

    def test_volume24hr_passes_check(self, client):
        """Test that volume24hr can satisfy the volume requirement"""
        markets = [
            {"active": True, "closed": False, "volume": 0, "volume24hr": 100},
        ]

        result = client.filter_fresh_markets(markets, require_volume=True, min_volume=50)
        assert len(result) == 1

    def test_require_volume_false_skips_volume_check(self, client):
        """Test that require_volume=False skips volume filtering"""
        markets = [
            {"active": True, "closed": False, "volume": 0},
        ]

        result = client.filter_fresh_markets(markets, require_volume=False)
        assert len(result) == 1

    def test_empty_list(self, client):
        """Test with empty market list"""
        result = client.filter_fresh_markets([])
        assert result == []

    def test_all_filtered_out(self, client):
        """Test when all markets are filtered out"""
        markets = [
            {"active": False, "closed": True, "volume": 0},
        ]

        result = client.filter_fresh_markets(markets)
        assert result == []

    def test_none_volume_handled(self, client):
        """Test that None volume values are handled (converted to 0)"""
        markets = [
            {"active": True, "closed": False, "volume": None, "volume24hr": None},
        ]

        result = client.filter_fresh_markets(markets, require_volume=True, min_volume=1)
        assert len(result) == 0


class TestGammaClientInit:
    """Test GammaClient initialization"""

    def test_default_base_url(self):
        """Test default base URL"""
        client = GammaClient()
        assert client.base_url == GAMMA_ENDPOINT

    def test_custom_base_url(self):
        """Test custom base URL with trailing slash stripped"""
        client = GammaClient(base_url="https://custom.example.com/")
        assert client.base_url == "https://custom.example.com"

    def test_api_key_set_in_headers(self):
        """Test that API key is set in session headers"""
        client = GammaClient(api_key="test-key-123")
        assert client.session.headers.get("Authorization") == "Bearer test-key-123"

    def test_no_api_key_no_auth_header(self):
        """Test that no API key means no Authorization header"""
        client = GammaClient()
        assert "Authorization" not in client.session.headers

    def test_rate_limiter_created(self):
        """Test that rate limiter is created"""
        client = GammaClient()
        assert isinstance(client.rate_limiter, RateLimiter)
        assert client.rate_limiter.requests_per_minute == 60

    def test_close_session(self):
        """Test that close() closes the session"""
        client = GammaClient()
        with patch.object(client.session, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()
