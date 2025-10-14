"""Tests for CLOB API client"""

import pytest
import responses
from polyterm.api.clob import CLOBClient


class TestCLOBClient:
    """Test CLOB API client"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return CLOBClient(
            rest_endpoint="https://test-clob.polymarket.com",
            ws_endpoint="wss://test-clob.polymarket.com/ws",
        )
    
    @responses.activate
    def test_get_order_book(self, client):
        """Test getting order book"""
        responses.add(
            responses.GET,
            "https://test-clob.polymarket.com/book/123",
            json={
                "bids": [
                    ["0.65", "1000"],
                    ["0.64", "2000"],
                ],
                "asks": [
                    ["0.66", "1500"],
                    ["0.67", "2500"],
                ],
            },
            status=200,
        )
        
        order_book = client.get_order_book("123", depth=20)
        assert len(order_book["bids"]) == 2
        assert len(order_book["asks"]) == 2
        assert order_book["bids"][0][0] == "0.65"
    
    @responses.activate
    def test_get_ticker(self, client):
        """Test getting ticker data"""
        responses.add(
            responses.GET,
            "https://test-clob.polymarket.com/ticker/123",
            json={
                "last": "0.65",
                "volume_24h": "50000",
                "high_24h": "0.70",
                "low_24h": "0.60",
            },
            status=200,
        )
        
        ticker = client.get_ticker("123")
        assert ticker["last"] == "0.65"
        assert ticker["volume_24h"] == "50000"
    
    @responses.activate
    def test_get_recent_trades(self, client):
        """Test getting recent trades"""
        responses.add(
            responses.GET,
            "https://test-clob.polymarket.com/trades/123",
            json=[
                {"id": "1", "price": "0.65", "size": "100", "side": "buy"},
                {"id": "2", "price": "0.64", "size": "200", "side": "sell"},
            ],
            status=200,
        )
        
        trades = client.get_recent_trades("123", limit=100)
        assert len(trades) == 2
        assert trades[0]["price"] == "0.65"
    
    def test_calculate_spread(self, client):
        """Test spread calculation"""
        order_book = {
            "bids": [["0.64", "1000"]],
            "asks": [["0.66", "1000"]],
        }
        
        spread = client.calculate_spread(order_book)
        expected_spread = ((0.66 - 0.64) / 0.64) * 100
        assert abs(spread - expected_spread) < 0.01
    
    def test_calculate_spread_empty_book(self, client):
        """Test spread calculation with empty book"""
        order_book = {"bids": [], "asks": []}
        spread = client.calculate_spread(order_book)
        assert spread == 0.0
    
    def test_detect_large_trade(self, client):
        """Test whale trade detection"""
        large_trade = {"size": "10000", "price": "0.65"}
        small_trade = {"size": "100", "price": "0.65"}
        
        assert client.detect_large_trade(large_trade, threshold=5000) is True
        assert client.detect_large_trade(small_trade, threshold=5000) is False
    
    @responses.activate
    def test_get_market_depth(self, client):
        """Test getting market depth"""
        responses.add(
            responses.GET,
            "https://test-clob.polymarket.com/depth/123",
            json={
                "bid_depth": 10000,
                "ask_depth": 12000,
                "total_depth": 22000,
            },
            status=200,
        )
        
        depth = client.get_market_depth("123")
        assert depth["bid_depth"] == 10000
        assert depth["total_depth"] == 22000

