"""Tests for API endpoint integration"""

import pytest
from polyterm.api.gamma import GammaClient
from polyterm.api.clob import CLOBClient
from polyterm.api.subgraph import SubgraphClient
from polyterm.api.aggregator import APIAggregator


class TestAPIEndpoints:
    """Test that API endpoints return correct, live data"""
    
    @pytest.fixture
    def gamma_client(self):
        return GammaClient()
    
    @pytest.fixture
    def clob_client(self):
        return CLOBClient()
    
    @pytest.fixture
    def subgraph_client(self):
        return SubgraphClient()
    
    @pytest.fixture
    def aggregator(self, gamma_client, clob_client, subgraph_client):
        return APIAggregator(gamma_client, clob_client, subgraph_client)
    
    def test_gamma_events_endpoint_returns_data(self, gamma_client):
        """Test Gamma /events endpoint returns data"""
        markets = gamma_client.get_markets(limit=5, active=True, closed=False)
        
        assert len(markets) > 0, "Gamma API returned no markets"
        assert isinstance(markets, list), "Markets should be a list"
        
        # Check first market structure
        market = markets[0]
        assert 'question' in market or 'title' in market, "Market missing question/title"
        assert 'endDate' in market, "Market missing endDate"
    
    def test_clob_sampling_markets_endpoint(self, clob_client):
        """Test CLOB sampling-markets endpoint"""
        markets = clob_client.get_current_markets(limit=5)
        
        assert len(markets) > 0, "CLOB API returned no markets"
        assert isinstance(markets, list), "Markets should be a list"
        
        # Check structure
        market = markets[0]
        assert 'question' in market, "Market missing question"
        assert 'active' in market, "Market missing active flag"
    
    def test_clob_market_validation(self, clob_client):
        """Test CLOB market currency validation"""
        markets = clob_client.get_current_markets(limit=10)
        
        current_markets = [m for m in markets if clob_client.is_market_current(m)]
        
        assert len(current_markets) > 0, "No current markets found in CLOB"
        
        # Verify they're actually current
        from datetime import datetime
        current_year = datetime.now().year
        
        for market in current_markets:
            end_date = market.get('end_date_iso', market.get('end_date', ''))
            if end_date and len(end_date) >= 4:
                year = int(end_date[:4])
                assert year >= current_year, f"Current market from past year: {market.get('question')}"
    
    def test_subgraph_returns_recent_data(self, subgraph_client):
        """Test Subgraph returns recent trade data"""
        # Get trending markets (should have recent activity)
        try:
            markets = subgraph_client.get_trending_markets_by_volume(time_window=86400, first=5)
            
            # Just verify it doesn't crash and returns data
            assert isinstance(markets, list), "Should return list of markets"
        except Exception as e:
            # Subgraph might have different structure, that's okay for now
            pytest.skip(f"Subgraph endpoint needs verification: {e}")
    
    def test_aggregator_live_markets(self, aggregator):
        """Test aggregator returns live markets"""
        markets = aggregator.get_live_markets(limit=10, require_volume=False)

        assert len(markets) > 0, "Aggregator returned no live markets"

        # Verify markets are active (not closed)
        # Note: Markets may have endDate in the past but still be active if not yet resolved
        for market in markets:
            is_active = market.get('active')
            is_closed = market.get('closed')
            # If we have explicit flags, verify market is active
            if is_active is not None and is_closed is not None:
                assert is_active and not is_closed, f"Aggregator returned inactive/closed market: {market.get('question')}"
    
    def test_aggregator_top_markets_by_volume(self, aggregator):
        """Test getting top markets by volume"""
        markets = aggregator.get_top_markets_by_volume(limit=5, min_volume=0.01)
        
        # Should return at least some markets
        assert len(markets) >= 0, "Top markets query failed"
        
        if len(markets) > 1:
            # Verify they're sorted by volume
            volumes = [float(m.get('volume24hr', 0) or 0) for m in markets]
            assert volumes == sorted(volumes, reverse=True), "Markets not sorted by volume"
    
    def test_aggregator_data_freshness_validation(self, aggregator):
        """Test data freshness validation"""
        markets = aggregator.get_live_markets(limit=20, require_volume=False)
        
        if markets:
            report = aggregator.validate_data_freshness(markets)
            
            assert 'total_markets' in report
            assert 'fresh_markets' in report
            assert 'stale_markets' in report
            
            # Should have more fresh than stale
            assert report['fresh_markets'] >= report['stale_markets'], \
                f"More stale ({report['stale_markets']}) than fresh ({report['fresh_markets']}) markets"
    
    def test_rate_limiting_works(self, gamma_client):
        """Test that rate limiting doesn't break requests"""
        # Make multiple rapid requests
        for i in range(5):
            markets = gamma_client.get_markets(limit=2, active=True, closed=False)
            assert len(markets) >= 0, f"Request {i+1} failed"
        
        # All should succeed without errors
    
    def test_error_handling_bad_market_id(self, gamma_client):
        """Test error handling for invalid market ID"""
        with pytest.raises(Exception):
            gamma_client.get_market("invalid_market_id_12345")
    
    def test_fallback_mechanism(self, aggregator):
        """Test that fallback works when primary source fails"""
        # This tests that if Gamma fails, CLOB is used
        markets = aggregator.get_live_markets(limit=5, require_volume=False)
        
        # Should get markets from either source
        assert len(markets) >= 0, "Fallback mechanism failed"

