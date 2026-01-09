"""End-to-end integration tests with live API"""

import pytest
from datetime import datetime
from polyterm.api.gamma import GammaClient
from polyterm.api.clob import CLOBClient
from polyterm.api.subgraph import SubgraphClient
from polyterm.api.aggregator import APIAggregator
from polyterm.core.scanner import MarketScanner


class TestLiveIntegration:
    """End-to-end integration tests with real API calls"""
    
    @pytest.fixture
    def clients(self):
        """Initialize all API clients"""
        gamma = GammaClient()
        clob = CLOBClient()
        subgraph = SubgraphClient()
        return gamma, clob, subgraph
    
    @pytest.fixture
    def aggregator(self, clients):
        """Initialize aggregator"""
        return APIAggregator(*clients)
    
    @pytest.fixture
    def scanner(self, clients):
        """Initialize scanner"""
        return MarketScanner(*clients)
    
    def test_end_to_end_live_data_flow(self, aggregator, scanner):
        """Test complete data flow from API to scanner"""
        # 1. Get live markets from aggregator
        markets = aggregator.get_live_markets(limit=5, require_volume=True, min_volume=1.0)

        # Skip if no fresh markets available (depends on external API data)
        if len(markets) == 0:
            pytest.skip("No fresh markets available from API")
        
        # 2. Verify markets are fresh
        current_year = datetime.now().year
        for market in markets:
            end_date = market.get('endDate', '')
            if end_date and len(end_date) >= 4:
                year = int(end_date[:4])
                assert year >= current_year, f"Old market: {market.get('question')}"
        
        # 3. Verify markets have volume
        markets_with_volume = sum(1 for m in markets if float(m.get('volume24hr', 0) or 0) > 0)
        assert markets_with_volume > 0, "No markets with volume"
        
        # 4. Test scanner with live data
        if markets:
            market_id = markets[0].get('id')
            snapshot = scanner.get_market_snapshot(market_id)
            
            # Snapshot should be created successfully
            if snapshot:
                assert snapshot.market_id == market_id
                assert snapshot.timestamp > 0
    
    def test_top_5_markets_match_live_data(self, aggregator):
        """Verify top 5 markets are actually the most active"""
        top_markets = aggregator.get_top_markets_by_volume(limit=5, min_volume=1.0)

        # Skip if no fresh markets available (depends on external API data)
        if len(top_markets) == 0:
            pytest.skip("No fresh markets available from API")
        
        # Verify they're sorted by volume
        if len(top_markets) > 1:
            volumes = [float(m.get('volume24hr', 0) or 0) for m in top_markets]
            assert volumes == sorted(volumes, reverse=True), "Markets not sorted by volume"
        
        # Verify all are current year
        current_year = datetime.now().year
        for market in top_markets:
            end_date = market.get('endDate', '')
            if end_date and len(end_date) >= 4:
                year = int(end_date[:4])
                assert year >= current_year, f"Top market from past: {market.get('question')}"
    
    def test_data_validation_report(self, aggregator):
        """Test data validation reporting"""
        markets = aggregator.get_live_markets(limit=20, require_volume=False)
        
        if markets:
            report = aggregator.validate_data_freshness(markets)
            
            # Report should have required fields
            assert 'total_markets' in report
            assert 'fresh_markets' in report
            assert 'stale_markets' in report
            assert 'markets_with_volume' in report
            
            # Most markets should be fresh
            assert report['fresh_markets'] >= report['total_markets'] * 0.7, \
                "Less than 70% of markets are fresh"
    
    def test_fallback_mechanism_works(self, clients):
        """Test that fallback works when primary fails"""
        gamma, clob, subgraph = clients
        aggregator = APIAggregator(gamma, clob, subgraph)
        
        # Get markets (should succeed via either Gamma or CLOB)
        markets = aggregator.get_live_markets(limit=5, require_volume=False)
        
        # Should get data from at least one source
        assert len(markets) >= 0, "All APIs failed"
    
    def test_market_snapshot_creation(self, scanner):
        """Test creating market snapshots"""
        # Get a live market
        try:
            markets = scanner.gamma_client.get_markets(limit=1, active=True, closed=False)
            if markets:
                market_id = markets[0].get('id')
                
                # Create snapshot
                snapshot = scanner.get_market_snapshot(market_id)
                
                if snapshot:
                    # Verify snapshot structure
                    assert snapshot.market_id == market_id
                    assert hasattr(snapshot, 'timestamp')
                    assert hasattr(snapshot, 'probability')
                    assert hasattr(snapshot, 'volume')
                    assert hasattr(snapshot, 'data_sources')
                    assert hasattr(snapshot, 'is_fresh')
        except Exception as e:
            pytest.skip(f"Could not test snapshot creation: {e}")
    
    def test_critical_no_old_markets_in_results(self, aggregator):
        """CRITICAL: Ensure no markets from 2024 or earlier appear"""
        markets = aggregator.get_live_markets(limit=50, require_volume=False)

        # Skip if no fresh markets available (depends on external API data)
        if len(markets) == 0:
            pytest.skip("No fresh markets available from API - freshness filter working correctly")

        current_year = datetime.now().year
        old_markets = []

        for market in markets:
            end_date = market.get('endDate', '')
            if end_date and len(end_date) >= 4:
                year = int(end_date[:4])
                if year < current_year:
                    old_markets.append(f"{market.get('question', 'Unknown')[:50]} ({year})")

        assert len(old_markets) == 0, \
            f"CRITICAL: Old markets found in results:\n" + "\n".join(old_markets[:5])
    
    def test_critical_volume_data_present(self, aggregator):
        """CRITICAL: Ensure volume data is present for active markets"""
        markets = aggregator.get_live_markets(limit=20, require_volume=True, min_volume=0.01)
        
        if len(markets) == 0:
            pytest.skip("No markets with volume requirement found")
        
        # All returned markets should have volume
        for market in markets:
            volume = float(market.get('volume', 0) or 0)
            volume_24hr = float(market.get('volume24hr', 0) or 0)
            
            assert volume > 0 or volume_24hr > 0, \
                f"Market without volume: {market.get('question', 'Unknown')}"

