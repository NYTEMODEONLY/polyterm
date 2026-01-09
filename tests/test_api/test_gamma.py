"""Tests for Gamma Markets API client"""

import pytest
import responses
from polyterm.api.gamma import GammaClient, RateLimiter


class TestRateLimiter:
    """Test rate limiter functionality"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly"""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert limiter.min_interval == 1.0
    
    def test_rate_limiter_waits(self):
        """Test rate limiter enforces delays"""
        import time
        limiter = RateLimiter(requests_per_minute=120)  # 2 per second
        
        start = time.time()
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # Should have waited at least min_interval
        assert elapsed >= limiter.min_interval


class TestGammaClient:
    """Test Gamma API client"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return GammaClient(base_url="https://test-api.polymarket.com")
    
    @responses.activate
    def test_get_markets(self, client):
        """Test getting markets list"""
        # Note: get_markets uses /events endpoint, not /markets
        responses.add(
            responses.GET,
            "https://test-api.polymarket.com/events",
            json=[
                {"id": "1", "question": "Test Market 1", "volume": 10000},
                {"id": "2", "question": "Test Market 2", "volume": 20000},
            ],
            status=200,
        )

        markets = client.get_markets(limit=10)
        assert len(markets) == 2
        assert markets[0]["id"] == "1"
        assert markets[1]["question"] == "Test Market 2"
    
    @responses.activate
    def test_get_market(self, client):
        """Test getting single market"""
        responses.add(
            responses.GET,
            "https://test-api.polymarket.com/markets/123",
            json={
                "id": "123",
                "question": "Will Bitcoin reach $100k?",
                "volume": 50000,
                "liquidity": 25000,
            },
            status=200,
        )
        
        market = client.get_market("123")
        assert market["id"] == "123"
        assert market["question"] == "Will Bitcoin reach $100k?"
        assert market["volume"] == 50000
    
    @responses.activate
    def test_get_market_prices(self, client):
        """Test getting market prices"""
        responses.add(
            responses.GET,
            "https://test-api.polymarket.com/markets/123/prices",
            json={"price": 0.65, "timestamp": 1234567890},
            status=200,
        )
        
        prices = client.get_market_prices("123")
        assert prices["price"] == 0.65
        assert "timestamp" in prices
    
    @responses.activate
    def test_search_markets(self, client):
        """Test market search"""
        responses.add(
            responses.GET,
            "https://test-api.polymarket.com/markets/search",
            json=[
                {"id": "1", "question": "Bitcoin price prediction"},
                {"id": "2", "question": "Ethereum price prediction"},
            ],
            status=200,
        )
        
        results = client.search_markets("bitcoin", limit=5)
        assert len(results) == 2
        assert "Bitcoin" in results[0]["question"]
    
    @responses.activate
    def test_api_error_handling(self, client):
        """Test API error handling"""
        responses.add(
            responses.GET,
            "https://test-api.polymarket.com/markets/999",
            json={"error": "Not found"},
            status=404,
        )
        
        with pytest.raises(Exception) as exc_info:
            client.get_market("999")
        assert "API request failed" in str(exc_info.value)
    
    @responses.activate
    def test_get_market_volume(self, client):
        """Test getting market volume data"""
        responses.add(
            responses.GET,
            "https://test-api.polymarket.com/markets/123/volume",
            json=[
                {"timestamp": 1000, "volume": 5000},
                {"timestamp": 2000, "volume": 7000},
            ],
            status=200,
        )
        
        volume_data = client.get_market_volume("123", interval="1h")
        assert len(volume_data) == 2
        assert volume_data[0]["volume"] == 5000
    
    @responses.activate
    def test_get_trending_markets(self, client):
        """Test getting trending markets"""
        responses.add(
            responses.GET,
            "https://test-api.polymarket.com/markets/trending",
            json=[
                {"id": "1", "question": "Trending Market 1", "volume": 100000},
                {"id": "2", "question": "Trending Market 2", "volume": 80000},
            ],
            status=200,
        )
        
        trending = client.get_trending_markets(limit=10)
        assert len(trending) == 2
        assert trending[0]["volume"] == 100000

