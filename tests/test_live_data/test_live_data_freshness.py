"""Tests for live data freshness validation"""

import pytest
from datetime import datetime
from polyterm.api.gamma import GammaClient
from polyterm.api.aggregator import APIAggregator


class TestLiveDataFreshness:
    """Test that API returns fresh, current data"""
    
    @pytest.fixture
    def gamma_client(self):
        """Create Gamma API client"""
        return GammaClient()
    
    def test_markets_are_from_current_year(self, gamma_client):
        """Verify all markets are from current year (2025) or future"""
        markets = gamma_client.get_markets(limit=10, active=True, closed=False)
        
        current_year = datetime.now().year
        
        for market in markets:
            end_date = market.get('endDate', '')
            assert end_date, f"Market missing end date: {market.get('question')}"
            
            # Extract year from ISO date
            year = int(end_date[:4])
            assert year >= current_year, f"Market from past year {year}: {market.get('question')}"
    
    def test_no_closed_markets_returned(self, gamma_client):
        """Verify no closed markets are returned when requesting active"""
        markets = gamma_client.get_markets(limit=20, active=True, closed=False)
        
        for market in markets:
            assert not market.get('closed', False), f"Closed market returned: {market.get('question')}"
    
    def test_markets_have_volume_data(self, gamma_client):
        """Verify markets have volume data (not all zeros)"""
        markets = gamma_client.get_markets(limit=10, active=True, closed=False)
        
        markets_with_volume = 0
        
        for market in markets:
            volume = float(market.get('volume', 0) or 0)
            volume_24hr = float(market.get('volume24hr', 0) or 0)
            
            if volume > 0 or volume_24hr > 0:
                markets_with_volume += 1
        
        # At least 50% of markets should have volume data
        assert markets_with_volume >= len(markets) * 0.5, \
            f"Only {markets_with_volume}/{len(markets)} markets have volume data"
    
    def test_timestamps_are_recent(self, gamma_client):
        """Verify market end dates are in the future or very recent past"""
        markets = gamma_client.get_markets(limit=10, active=True, closed=False)
        
        from dateutil import parser
        now = datetime.now()
        
        for market in markets:
            end_date_str = market.get('endDate', '')
            if end_date_str:
                end_date = parser.parse(end_date_str)
                
                # End date should be in the future for active markets
                # Allow some tolerance for recently closed
                hours_until_end = (end_date - now).total_seconds() / 3600
                
                assert hours_until_end > -24, \
                    f"Market ended too long ago: {market.get('question')} (ended {abs(hours_until_end):.1f} hours ago)"
    
    def test_is_market_fresh_validation(self, gamma_client):
        """Test the is_market_fresh validation method"""
        markets = gamma_client.get_markets(limit=10, active=True, closed=False)
        
        fresh_count = 0
        for market in markets:
            if gamma_client.is_market_fresh(market, max_age_hours=24):
                fresh_count += 1
        
        # All active markets should be fresh
        assert fresh_count == len(markets), \
            f"Only {fresh_count}/{len(markets)} markets are fresh"
    
    def test_filter_fresh_markets(self, gamma_client):
        """Test filtering for fresh markets only"""
        # Get all markets (may include some old ones)
        all_markets = gamma_client.get_markets(limit=50, active=True, closed=False)
        
        # Filter for fresh markets
        fresh_markets = gamma_client.filter_fresh_markets(
            all_markets,
            max_age_hours=24,
            require_volume=False
        )
        
        # Verify all filtered markets are fresh
        for market in fresh_markets:
            assert gamma_client.is_market_fresh(market, max_age_hours=24), \
                f"Filtered market is not fresh: {market.get('question')}"
    
    def test_volume_filtering(self, gamma_client):
        """Test filtering markets by volume threshold"""
        markets = gamma_client.get_markets(limit=50, active=True, closed=False)
        
        # Filter with volume requirement
        volume_markets = gamma_client.filter_fresh_markets(
            markets,
            max_age_hours=24,
            require_volume=True,
            min_volume=1.0
        )
        
        # All filtered markets should have volume
        for market in volume_markets:
            volume = float(market.get('volume', 0) or 0)
            volume_24hr = float(market.get('volume24hr', 0) or 0)
            
            assert volume >= 1.0 or volume_24hr >= 1.0, \
                f"Market doesn't meet volume threshold: {market.get('question')}"

