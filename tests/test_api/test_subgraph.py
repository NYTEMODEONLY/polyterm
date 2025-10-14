"""Tests for Subgraph API client"""

import pytest
from unittest.mock import Mock, patch
from polyterm.api.subgraph import SubgraphClient


class TestSubgraphClient:
    """Test Subgraph GraphQL client"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        with patch('polyterm.api.subgraph.Client'):
            return SubgraphClient(endpoint="https://test-subgraph.polymarket.com")
    
    def test_get_market_trades(self, client):
        """Test getting market trades"""
        mock_result = {
            "trades": [
                {
                    "id": "1",
                    "trader": "0x123",
                    "market": "market1",
                    "shares": "100",
                    "price": "0.65",
                    "timestamp": "1234567890",
                },
                {
                    "id": "2",
                    "trader": "0x456",
                    "market": "market1",
                    "shares": "200",
                    "price": "0.66",
                    "timestamp": "1234567900",
                },
            ]
        }
        
        client.client.execute = Mock(return_value=mock_result)
        
        trades = client.get_market_trades("market1", first=100)
        assert len(trades) == 2
        assert trades[0]["trader"] == "0x123"
        assert trades[1]["shares"] == "200"
    
    def test_get_market_statistics(self, client):
        """Test getting market statistics"""
        mock_result = {
            "market": {
                "id": "market1",
                "question": "Will Bitcoin reach $100k?",
                "totalVolume": "50000",
                "totalLiquidity": "25000",
                "tradeCount": "150",
            }
        }
        
        client.client.execute = Mock(return_value=mock_result)
        
        stats = client.get_market_statistics("market1")
        assert stats["id"] == "market1"
        assert stats["totalVolume"] == "50000"
        assert stats["tradeCount"] == "150"
    
    def test_get_whale_trades(self, client):
        """Test getting whale trades"""
        mock_result = {
            "trades": [
                {
                    "id": "1",
                    "trader": "0x789",
                    "shares": "10000",
                    "price": "0.65",
                    "timestamp": "1234567890",
                },
                {
                    "id": "2",
                    "trader": "0xabc",
                    "shares": "500",
                    "price": "0.66",
                    "timestamp": "1234567900",
                },
            ]
        }
        
        client.client.execute = Mock(return_value=mock_result)
        
        whale_trades = client.get_whale_trades(min_notional=5000)
        # Should filter out trade 2 (500 * 0.66 = 330 < 5000)
        assert len(whale_trades) == 1
        assert float(whale_trades[0]["shares"]) * float(whale_trades[0]["price"]) >= 5000
    
    def test_get_user_positions(self, client):
        """Test getting user positions"""
        mock_result = {
            "positions": [
                {
                    "id": "1",
                    "user": "0x123",
                    "market": "market1",
                    "shares": "100",
                    "averagePrice": "0.65",
                    "realizedPnL": "50",
                    "unrealizedPnL": "25",
                },
            ]
        }
        
        client.client.execute = Mock(return_value=mock_result)
        
        positions = client.get_user_positions("0x123")
        assert len(positions) == 1
        assert positions[0]["user"] == "0x123"
        assert positions[0]["market"] == "market1"
    
    def test_get_market_volume(self, client):
        """Test getting market volume"""
        mock_result = {
            "market": {
                "id": "market1",
                "totalVolume": "50000",
                "totalLiquidity": "25000",
                "trades": [
                    {"shares": "100", "price": "0.65"},
                    {"shares": "200", "price": "0.66"},
                ],
            }
        }
        
        client.client.execute = Mock(return_value=mock_result)
        
        volume_data = client.get_market_volume("market1", start_time=1000, end_time=2000)
        assert volume_data["id"] == "market1"
        assert volume_data["totalVolume"] == "50000"
        assert len(volume_data["trades"]) == 2
    
    def test_get_liquidity_changes(self, client):
        """Test getting liquidity changes"""
        mock_result = {
            "liquidityEvents": [
                {
                    "id": "1",
                    "type": "add",
                    "provider": "0x123",
                    "amount": "10000",
                    "timestamp": "1234567890",
                },
                {
                    "id": "2",
                    "type": "remove",
                    "provider": "0x456",
                    "amount": "5000",
                    "timestamp": "1234567900",
                },
            ]
        }
        
        client.client.execute = Mock(return_value=mock_result)
        
        events = client.get_market_liquidity_changes("market1", first=100)
        assert len(events) == 2
        assert events[0]["type"] == "add"
        assert events[1]["type"] == "remove"
    
    def test_get_trending_markets(self, client):
        """Test getting trending markets by volume"""
        mock_result = {
            "markets": [
                {
                    "id": "market1",
                    "question": "Market 1",
                    "totalVolume": "100000",
                    "tradeCount": "500",
                },
                {
                    "id": "market2",
                    "question": "Market 2",
                    "totalVolume": "80000",
                    "tradeCount": "400",
                },
            ]
        }
        
        client.client.execute = Mock(return_value=mock_result)
        
        trending = client.get_trending_markets_by_volume(time_window=86400, first=10)
        assert len(trending) == 2
        assert int(trending[0]["totalVolume"]) > int(trending[1]["totalVolume"])

