"""Tests for analytics engine"""

import pytest
from unittest.mock import Mock
from polyterm.core.analytics import AnalyticsEngine, WhaleActivity


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
        subgraph = Mock()
        return gamma, clob, subgraph
    
    @pytest.fixture
    def analytics(self, mock_clients):
        """Create test analytics engine"""
        gamma, clob, subgraph = mock_clients
        return AnalyticsEngine(gamma, clob, subgraph)
    
    def test_track_whale_trades(self, analytics, mock_clients):
        """Test tracking whale trades via volume spike detection"""
        gamma, clob, subgraph = mock_clients

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

        # Should find 2 markets with significant volume (whale activity proxy)
        assert len(whale_trades) == 2
        # Whale trades are volume-based, verify structure (order may vary)
        market_ids = {wt.market_id for wt in whale_trades}
        assert market_ids == {"market1", "market2"}
    
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
    
    def test_analyze_historical_trends(self, analytics, mock_clients):
        """Test historical trend analysis"""
        gamma, clob, subgraph = mock_clients
        
        subgraph.get_market_statistics.return_value = {
            "id": "market1",
            "totalVolume": "50000",
            "tradeCount": "150",
        }
        
        import time
        current_time = int(time.time())
        
        subgraph.get_market_volume.return_value = {}
        
        subgraph.get_market_trades.return_value = [
            {"shares": "100", "price": "0.50", "timestamp": str(current_time - 3600)},
            {"shares": "200", "price": "0.60", "timestamp": str(current_time - 7200)},
            {"shares": "150", "price": "0.65", "timestamp": str(current_time - 10800)},
        ]
        
        trends = analytics.analyze_historical_trends("market1", hours=24)
        
        assert trends["market_id"] == "market1"
        assert trends["total_trades"] == 3
        assert trends["total_volume"] > 0
        assert "trend_direction" in trends
    
    def test_predict_price_movement(self, analytics, mock_clients):
        """Test price prediction"""
        gamma, clob, subgraph = mock_clients
        
        # Mock historical trends
        subgraph.get_market_statistics.return_value = {"id": "market1"}
        subgraph.get_market_volume.return_value = {}
        
        import time
        current_time = int(time.time())
        
        # Upward trend
        subgraph.get_market_trades.return_value = [
            {"shares": "100", "price": "0.70", "timestamp": str(current_time - 1000)},
            {"shares": "100", "price": "0.50", "timestamp": str(current_time - 100000)},
        ]
        
        subgraph.get_whale_trades.return_value = []
        
        prediction = analytics.predict_price_movement("market1", horizon_hours=24)
        
        assert "prediction" in prediction
        assert "confidence" in prediction
        assert prediction["prediction"] in ["up", "down", "stable"]
    
    def test_get_portfolio_analytics(self, analytics, mock_clients):
        """Test portfolio analytics"""
        gamma, clob, subgraph = mock_clients
        
        subgraph.get_user_positions.return_value = [
            {
                "shares": "100",
                "averagePrice": "0.65",
                "realizedPnL": "50",
                "unrealizedPnL": "25",
            },
            {
                "shares": "200",
                "averagePrice": "0.50",
                "realizedPnL": "100",
                "unrealizedPnL": "-20",
            },
        ]
        
        portfolio = analytics.get_portfolio_analytics("0x123")
        
        assert portfolio["wallet_address"] == "0x123"
        assert portfolio["total_positions"] == 2
        assert portfolio["total_value"] > 0
        assert portfolio["total_pnl"] == 155  # 50 + 25 + 100 - 20

    def test_get_portfolio_analytics_uses_data_api_when_subgraph_missing(self, mock_clients):
        """Test portfolio analytics uses Data API when Subgraph is unavailable."""
        gamma, clob, _ = mock_clients

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

        analytics = AnalyticsEngine(gamma, clob, None, data_api_client=data_api)
        portfolio = analytics.get_portfolio_analytics("0x123")

        assert portfolio["wallet_address"] == "0x123"
        assert portfolio["total_positions"] == 1
        assert portfolio["total_value"] == 80
        assert portfolio["total_invested"] == 65
        assert portfolio["total_pnl"] == 15
        assert portfolio["data_source"] == "data_api"

    def test_get_portfolio_analytics_preserves_explicit_zero_values(self, mock_clients):
        """Explicit zero current/initial values should not be replaced by fallback math."""
        gamma, clob, _ = mock_clients

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

        analytics = AnalyticsEngine(gamma, clob, None, data_api_client=data_api)
        portfolio = analytics.get_portfolio_analytics("0x123")

        assert portfolio["total_positions"] == 1
        assert portfolio["total_value"] == 0
        assert portfolio["total_invested"] == 0
        assert portfolio["total_pnl"] == -65
        assert portfolio["roi_percent"] == 0

    def test_get_portfolio_analytics_falls_back_when_values_missing(self, mock_clients):
        """Missing value fields should still use shares*avg_price fallback."""
        gamma, clob, _ = mock_clients

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

        analytics = AnalyticsEngine(gamma, clob, None, data_api_client=data_api)
        portfolio = analytics.get_portfolio_analytics("0x123")

        assert portfolio["total_value"] == 5
        assert portfolio["total_invested"] == 5
    
    def test_detect_market_manipulation(self, analytics, mock_clients):
        """Test market manipulation detection"""
        gamma, clob, subgraph = mock_clients
        
        # Mock liquidity withdrawals
        subgraph.get_market_liquidity_changes.return_value = [
            {"type": "remove", "amount": "10000"},
            {"type": "remove", "amount": "5000"},
            {"type": "remove", "amount": "3000"},
            {"type": "remove", "amount": "2000"},
        ]
        
        # Mock suspicious trades
        subgraph.get_market_trades.return_value = [
            {"trader": "0x123", "price": "0.50"},
            {"trader": "0x123", "price": "0.52"},
            {"trader": "0x123", "price": "0.51"},
            {"trader": "0x123", "price": "0.53"},
        ]
        
        risk = analytics.detect_market_manipulation("market1")
        
        assert risk["market_id"] == "market1"
        assert risk["risk_level"] in ["low", "medium", "high"]
        assert len(risk["risk_factors"]) > 0
    
    def test_no_manipulation_detected(self, analytics, mock_clients):
        """Test when no manipulation is detected"""
        gamma, clob, subgraph = mock_clients
        
        subgraph.get_market_liquidity_changes.return_value = []
        subgraph.get_market_trades.return_value = [
            {"trader": "0x123", "price": "0.50"},
            {"trader": "0x456", "price": "0.51"},
        ]
        
        risk = analytics.detect_market_manipulation("market1")
        
        assert risk["risk_level"] == "low"
