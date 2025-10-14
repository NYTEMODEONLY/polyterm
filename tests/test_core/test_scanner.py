"""Tests for market scanner"""

import pytest
from unittest.mock import Mock, MagicMock
from polyterm.core.scanner import MarketScanner, MarketSnapshot


class TestMarketSnapshot:
    """Test MarketSnapshot class"""
    
    def test_snapshot_initialization(self):
        """Test snapshot initializes correctly"""
        data = {
            "market_id": "market1",
            "title": "Test Market",
            "probability": 65.0,
            "volume": 10000.0,
            "liquidity": 5000.0,
            "price": 0.65,
        }
        
        snapshot = MarketSnapshot("market1", data, 1234567890.0)
        assert snapshot.market_id == "market1"
        assert snapshot.probability == 65.0
        assert snapshot.volume == 10000.0
        assert snapshot.timestamp == 1234567890.0
    
    def test_calculate_shift(self):
        """Test shift calculation between snapshots"""
        data1 = {
            "probability": 50.0,
            "volume": 10000.0,
            "liquidity": 5000.0,
            "price": 0.50,
        }
        data2 = {
            "probability": 65.0,
            "volume": 15000.0,
            "liquidity": 6000.0,
            "price": 0.65,
        }
        
        snap1 = MarketSnapshot("market1", data1, 1000.0)
        snap2 = MarketSnapshot("market1", data2, 2000.0)
        
        changes = snap2.calculate_shift(snap1)
        
        assert changes["probability_change"] == 15.0
        assert changes["volume_change"] == 50.0  # 50% increase
        assert changes["liquidity_change"] == 20.0  # 20% increase


class TestMarketScanner:
    """Test MarketScanner class"""
    
    @pytest.fixture
    def mock_clients(self):
        """Create mock API clients"""
        gamma = Mock()
        clob = Mock()
        subgraph = Mock()
        return gamma, clob, subgraph
    
    @pytest.fixture
    def scanner(self, mock_clients):
        """Create test scanner"""
        gamma, clob, subgraph = mock_clients
        return MarketScanner(gamma, clob, subgraph, check_interval=60)
    
    def test_scanner_initialization(self, scanner):
        """Test scanner initializes correctly"""
        assert scanner.check_interval == 60
        assert scanner.max_snapshots_per_market == 100
        assert len(scanner.snapshots) == 0
    
    def test_store_snapshot(self, scanner):
        """Test snapshot storage"""
        data = {"probability": 65.0, "volume": 10000.0}
        snapshot = MarketSnapshot("market1", data, 1000.0)
        
        scanner.store_snapshot(snapshot)
        
        assert "market1" in scanner.snapshots
        assert len(scanner.snapshots["market1"]) == 1
        assert scanner.snapshots["market1"][0] == snapshot
    
    def test_snapshot_history_limit(self, scanner):
        """Test snapshot history is limited"""
        for i in range(150):
            data = {"probability": float(i), "volume": 1000.0}
            snapshot = MarketSnapshot("market1", data, float(i))
            scanner.store_snapshot(snapshot)
        
        # Should only keep last 100
        assert len(scanner.snapshots["market1"]) == 100
    
    def test_get_previous_snapshot(self, scanner):
        """Test getting previous snapshot"""
        data1 = {"probability": 50.0}
        data2 = {"probability": 60.0}
        
        snap1 = MarketSnapshot("market1", data1, 1000.0)
        snap2 = MarketSnapshot("market1", data2, 2000.0)
        
        scanner.store_snapshot(snap1)
        scanner.store_snapshot(snap2)
        
        previous = scanner.get_previous_snapshot("market1")
        assert previous == snap1
    
    def test_detect_shift_probability(self, scanner):
        """Test probability shift detection"""
        data1 = {"probability": 50.0, "volume": 10000.0, "liquidity": 5000.0}
        data2 = {"probability": 70.0, "volume": 10000.0, "liquidity": 5000.0}
        
        snap1 = MarketSnapshot("market1", data1, 1000.0)
        snap2 = MarketSnapshot("market1", data2, 2000.0)
        snap2.title = "Test Market"
        
        thresholds = {"probability": 10.0, "volume": 50.0, "liquidity": 30.0}
        
        shift = scanner.detect_shift(snap2, snap1, thresholds)
        
        assert shift is not None
        assert "probability" in shift["shift_type"]
        assert shift["changes"]["probability_change"] == 20.0
    
    def test_detect_shift_volume(self, scanner):
        """Test volume shift detection"""
        data1 = {"probability": 50.0, "volume": 10000.0, "liquidity": 5000.0}
        data2 = {"probability": 50.0, "volume": 20000.0, "liquidity": 5000.0}
        
        snap1 = MarketSnapshot("market1", data1, 1000.0)
        snap2 = MarketSnapshot("market1", data2, 2000.0)
        snap2.title = "Test Market"
        
        thresholds = {"probability": 10.0, "volume": 50.0, "liquidity": 30.0}
        
        shift = scanner.detect_shift(snap2, snap1, thresholds)
        
        assert shift is not None
        assert "volume" in shift["shift_type"]
    
    def test_no_shift_detected(self, scanner):
        """Test when no shift occurs"""
        data1 = {"probability": 50.0, "volume": 10000.0, "liquidity": 5000.0}
        data2 = {"probability": 52.0, "volume": 10500.0, "liquidity": 5100.0}
        
        snap1 = MarketSnapshot("market1", data1, 1000.0)
        snap2 = MarketSnapshot("market1", data2, 2000.0)
        
        thresholds = {"probability": 10.0, "volume": 50.0, "liquidity": 30.0}
        
        shift = scanner.detect_shift(snap2, snap1, thresholds)
        
        assert shift is None
    
    def test_add_shift_callback(self, scanner):
        """Test adding shift callbacks"""
        callback = Mock()
        scanner.add_shift_callback(callback)
        
        assert callback in scanner.shift_callbacks
    
    def test_calculate_volatility(self, scanner):
        """Test volatility calculation"""
        # Add snapshots with varying probabilities
        for i in range(15):
            prob = 50.0 + (i % 3) * 5  # Oscillating probabilities
            data = {"probability": prob, "volume": 10000.0}
            snapshot = MarketSnapshot("market1", data, float(i * 100))
            scanner.store_snapshot(snapshot)
        
        volatility = scanner.calculate_volatility("market1", window=10)
        
        # Should have some volatility
        assert volatility > 0
    
    def test_get_market_history(self, scanner):
        """Test getting market history"""
        import time
        current_time = time.time()
        
        # Add recent snapshots
        for i in range(5):
            data = {"probability": 50.0 + i, "volume": 10000.0}
            snapshot = MarketSnapshot("market1", data, current_time - (i * 3600))
            scanner.store_snapshot(snapshot)
        
        # Add old snapshot (25 hours ago)
        old_data = {"probability": 40.0, "volume": 5000.0}
        old_snapshot = MarketSnapshot("market1", old_data, current_time - (25 * 3600))
        scanner.store_snapshot(old_snapshot)
        
        # Get last 24 hours
        history = scanner.get_market_history("market1", hours=24)
        
        # Should only include recent snapshots
        assert len(history) == 5

