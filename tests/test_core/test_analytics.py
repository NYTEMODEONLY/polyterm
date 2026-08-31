"""Tests for analytics engine"""

import pytest
from unittest.mock import Mock
from polyterm.core.analytics import AnalyticsEngine, WhaleActivity
from polyterm.utils.errors import FeatureUnavailable


class TestWhaleActivity:
    """Test WhaleActivity class"""
    
    def test_whale_activity_creation(self):
        """Test whale activity initialization"""
        trade_data = {
            "trader": "0x123456789",
            "market": "market1",
            "outcome": "YES",
            "shares": "10000",
            "price": "0.65",
            "timestamp": "1234567890",
            "transactionHash": "0xabc",
        }
        
        whale = WhaleActivity(trade_data)
        
        assert whale.trader == "0x123456789"
        assert whale.market_id == "market1"
        assert whale.shares == 10000.0
        assert whale.price == 0.65
        assert whale.notional == 6500.0


class TestAnalyticsEngine:
    """Test AnalyticsEngine class"""
    
    @pytest.fixture
    def mock_clients(self):
        """Create mock API clients"""
        gamma = Mock()
        clob = Mock()
        return gamma, clob

    @pytest.fixture
    def analytics(self, mock_clients):
        """Create test analytics engine"""
        gamma, clob = mock_clients
        return AnalyticsEngine(gamma, clob)
    
    def test_track_whale_trades(self, analytics, mock_clients):
        """Test tracking whale trades via volume spike detection"""
        gamma, clob = mock_clients

        import time
        current_time = int(time.time())

        # track_whale_trades now uses Gamma API volume data, not subgraph
        gamma.get_markets.return_value = [
            {
                "id": "market1",
                "title": "Test Market 1",
                "volume24hr": 15000.0,  # Above min_notional threshold
                "probability": 0.65,
            },
            {
                "id": "market2",
                "title": "Test Market 2",
                "volume24hr": 25000.0,  # Above threshold
                "probability": 0.50,
            },
        ]

        whale_trades = analytics.track_whale_trades(
            min_notional=5000,
            lookback_hours=24,
        )

        # Should find 2 markets with significant volume (heuristic, not trader identity)
        assert len(whale_trades) == 2
        market_ids = {wt.market_id for wt in whale_trades}
        assert market_ids == {"market1", "market2"}
        assert all(wt.trader == "" for wt in whale_trades)
        assert all(wt.trader != "Volume Spike" for wt in whale_trades)
        assert all(wt.evidence_level == "gamma_volume24hr_heuristic" for wt in whale_trades)
    
    def test_get_whale_impact_on_market(self, analytics):
        """Test analyzing whale impact"""
        # Add some whale trades to cache
        analytics.known_whales["0x123"] = [
            WhaleActivity({
                "trader": "0x123",
                "market": "market1",
                "outcome": "YES",
                "shares": "10000",
                "price": "0.65",
                "notional": 6500.0,
            }),
            WhaleActivity({
                "trader": "0x123",
                "market": "market1",
                "outcome": "NO",
                "shares": "5000",
                "price": "0.35",
                "notional": 1750.0,
            }),
        ]
        
        impact = analytics.get_whale_impact_on_market("market1", "0x123")
        
        assert impact["total_trades"] == 2
        assert impact["total_volume"] == 8250.0
        assert impact["buy_volume"] == 6500.0
        assert impact["sell_volume"] == 1750.0
        assert impact["net_position"] == 4750.0
    
    def test_placeholder_analytics_raise_unavailable(self, analytics):
        """Placeholder analytics raise instead of returning empty/None/{}"""
        with pytest.raises(FeatureUnavailable) as exc:
            analytics.identify_whale_followers("0xabc")
        assert "identify_whale_followers" in exc.value.message

        with pytest.raises(FeatureUnavailable):
            analytics.calculate_market_correlation("m1", "m2")

        with pytest.raises(FeatureUnavailable):
            analytics.find_correlated_markets("m1")

        with pytest.raises(FeatureUnavailable):
            analytics.analyze_historical_trends("market1", hours=24)

        with pytest.raises(FeatureUnavailable):
            analytics.predict_price_movement("market1", horizon_hours=24)
    
    def test_get_portfolio_analytics_no_data_api(self, analytics):
        """Test portfolio analytics graceful degradation without data API"""
        portfolio = analytics.get_portfolio_analytics("0x123")

        assert portfolio["wallet_address"] == "0x123"
        # Should return graceful fallback (empty or error note)
        assert "total_positions" in portfolio

    def test_get_portfolio_analytics_uses_data_api_when_subgraph_missing(self, mock_clients):
        """Test portfolio analytics uses Data API when Subgraph is unavailable."""
        gamma, clob = mock_clients

        data_api = Mock()
        data_api.get_positions.return_value = [
            {
                "market": "market1",
                "size": "100",
                "averagePrice": "0.65",
                "currentValue": "80",
                "initialValue": "65",
                "pnl": "15",
            }
        ]

        analytics = AnalyticsEngine(gamma, clob, data_api_client=data_api)
        portfolio = analytics.get_portfolio_analytics("0x123")

        assert portfolio["wallet_address"] == "0x123"
        assert portfolio["total_positions"] == 1
        assert portfolio["total_value"] == 80
        assert portfolio["total_invested"] == 65
        assert portfolio["total_pnl"] == 15
        assert portfolio["data_source"] == "data_api"
        assert portfolio["source"] == "data_api"
        assert portfolio["lag"] is True
        assert portfolio["lagged"] is True

    def test_get_portfolio_analytics_preserves_explicit_zero_values(self, mock_clients):
        """Explicit zero current/initial values should not be replaced by fallback math."""
        gamma, clob = mock_clients

        data_api = Mock()
        data_api.get_positions.return_value = [
            {
                "market": "market-zero",
                "size": "100",
                "averagePrice": "0.65",
                "currentValue": "0",
                "initialValue": "0",
                "pnl": "-65",
            }
        ]

        analytics = AnalyticsEngine(gamma, clob, data_api_client=data_api)
        portfolio = analytics.get_portfolio_analytics("0x123")

        assert portfolio["total_positions"] == 1
        assert portfolio["total_value"] == 0
        assert portfolio["total_invested"] == 0
        assert portfolio["total_pnl"] == -65
        assert portfolio["roi_percent"] == 0

    def test_get_portfolio_analytics_falls_back_when_values_missing(self, mock_clients):
        """Missing value fields should still use shares*avg_price fallback."""
        gamma, clob = mock_clients

        data_api = Mock()
        data_api.get_positions.return_value = [
            {
                "market": "market-missing",
                "size": "10",
                "averagePrice": "0.5",
                # currentValue and initialValue intentionally omitted
                "pnl": "0",
            }
        ]

        analytics = AnalyticsEngine(gamma, clob, data_api_client=data_api)
        portfolio = analytics.get_portfolio_analytics("0x123")

        assert portfolio["total_value"] == 5
        assert portfolio["total_invested"] == 5
    
    def test_detect_market_manipulation_raises_unavailable(self, analytics):
        """Manipulation detection raises instead of a fake risk_score of 0"""
        with pytest.raises(FeatureUnavailable) as exc:
            analytics.detect_market_manipulation("market1")
        assert "detect_market_manipulation" in exc.value.message
