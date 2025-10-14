"""Tests for alert system"""

import pytest
from unittest.mock import Mock, patch
from polyterm.core.alerts import AlertManager, Alert, AlertLevel


class TestAlert:
    """Test Alert class"""
    
    def test_alert_creation(self):
        """Test alert creation"""
        alert = Alert(
            market_id="market1",
            title="Test Market",
            message="Probability increased by 15%",
            level=AlertLevel.WARNING,
            data={"change": 15.0},
        )
        
        assert alert.market_id == "market1"
        assert alert.title == "Test Market"
        assert alert.level == AlertLevel.WARNING
        assert alert.data["change"] == 15.0
    
    def test_alert_string_representation(self):
        """Test alert string formatting"""
        alert = Alert(
            market_id="market1",
            title="Test Market",
            message="Big move detected",
            level=AlertLevel.CRITICAL,
        )
        
        alert_str = str(alert)
        assert "CRITICAL" in alert_str
        assert "Test Market" in alert_str
        assert "Big move detected" in alert_str


class TestAlertManager:
    """Test AlertManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create test alert manager"""
        return AlertManager(enable_system_notifications=False)
    
    def test_manager_initialization(self, manager):
        """Test manager initializes correctly"""
        assert manager.max_history == 1000
        assert len(manager.alert_history) == 0
        assert len(manager.callbacks) == 0
    
    def test_add_callback(self, manager):
        """Test adding alert callback"""
        callback = Mock()
        manager.add_callback(callback)
        
        assert callback in manager.callbacks
    
    def test_create_probability_shift_alert(self, manager):
        """Test creating probability shift alert"""
        shift_data = {
            "market_id": "market1",
            "title": "Test Market",
            "changes": {"probability_change": 15.0},
        }
        
        alert = manager.create_probability_shift_alert(shift_data, threshold=10.0)
        
        assert alert is not None
        assert alert.market_id == "market1"
        assert "15.0%" in alert.message
        assert alert.level == AlertLevel.WARNING
    
    def test_create_probability_shift_alert_below_threshold(self, manager):
        """Test no alert when below threshold"""
        shift_data = {
            "market_id": "market1",
            "title": "Test Market",
            "changes": {"probability_change": 5.0},
        }
        
        alert = manager.create_probability_shift_alert(shift_data, threshold=10.0)
        
        assert alert is None
    
    def test_create_critical_probability_alert(self, manager):
        """Test critical alert for large probability shift"""
        shift_data = {
            "market_id": "market1",
            "title": "Test Market",
            "changes": {"probability_change": 25.0},
        }
        
        alert = manager.create_probability_shift_alert(shift_data, threshold=10.0)
        
        assert alert is not None
        assert alert.level == AlertLevel.CRITICAL
    
    def test_create_volume_spike_alert(self, manager):
        """Test creating volume spike alert"""
        shift_data = {
            "market_id": "market1",
            "title": "Test Market",
            "changes": {"volume_change": 75.0},
        }
        
        alert = manager.create_volume_spike_alert(shift_data, threshold=50.0)
        
        assert alert is not None
        assert "75.0%" in alert.message
        assert "spiked" in alert.message
    
    def test_create_liquidity_alert(self, manager):
        """Test creating liquidity alert"""
        shift_data = {
            "market_id": "market1",
            "title": "Test Market",
            "changes": {"liquidity_change": -40.0},
        }
        
        alert = manager.create_liquidity_alert(shift_data, threshold=30.0)
        
        assert alert is not None
        assert "40.0%" in alert.message
        assert alert.level == AlertLevel.WARNING
    
    def test_dispatch_alert(self, manager):
        """Test dispatching alerts"""
        callback = Mock()
        manager.add_callback(callback)
        
        alert = Alert(
            market_id="market1",
            title="Test Market",
            message="Test alert",
            level=AlertLevel.INFO,
        )
        
        with patch('sys.stdout.write'):
            manager.dispatch_alert(alert)
        
        # Check alert was stored
        assert len(manager.alert_history) == 1
        assert manager.alert_history[0] == alert
        
        # Check callback was called
        callback.assert_called_once_with(alert)
    
    def test_process_shift(self, manager):
        """Test processing shift data"""
        shift_data = {
            "market_id": "market1",
            "title": "Test Market",
            "changes": {
                "probability_change": 15.0,
                "volume_change": 60.0,
            },
        }
        
        thresholds = {
            "probability": 10.0,
            "volume": 50.0,
        }
        
        with patch('sys.stdout.write'):
            manager.process_shift(shift_data, thresholds)
        
        # Should create both probability and volume alerts
        assert len(manager.alert_history) >= 2
    
    def test_get_recent_alerts(self, manager):
        """Test getting recent alerts"""
        # Add multiple alerts
        for i in range(15):
            alert = Alert(
                market_id=f"market{i}",
                title=f"Market {i}",
                message=f"Alert {i}",
                level=AlertLevel.INFO,
            )
            with patch('sys.stdout.write'):
                manager.dispatch_alert(alert)
        
        recent = manager.get_recent_alerts(count=5)
        
        assert len(recent) == 5
        # Should be most recent
        assert recent[-1].message == "Alert 14"
    
    def test_get_alerts_for_market(self, manager):
        """Test getting alerts for specific market"""
        # Add alerts for different markets
        for i in range(5):
            alert = Alert(
                market_id="market1" if i % 2 == 0 else "market2",
                title=f"Market {i}",
                message=f"Alert {i}",
                level=AlertLevel.INFO,
            )
            with patch('sys.stdout.write'):
                manager.dispatch_alert(alert)
        
        market1_alerts = manager.get_alerts_for_market("market1")
        
        assert len(market1_alerts) == 3
        for alert in market1_alerts:
            assert alert.market_id == "market1"
    
    def test_alert_history_limit(self, manager):
        """Test alert history is limited"""
        # Create manager with small limit
        manager.max_history = 10
        
        # Add more alerts than limit
        for i in range(20):
            alert = Alert(
                market_id=f"market{i}",
                title=f"Market {i}",
                message=f"Alert {i}",
                level=AlertLevel.INFO,
            )
            with patch('sys.stdout.write'):
                manager.dispatch_alert(alert)
        
        # Should only keep last 10
        assert len(manager.alert_history) == 10
        assert manager.alert_history[0].message == "Alert 10"
    
    def test_clear_history(self, manager):
        """Test clearing alert history"""
        # Add some alerts
        for i in range(5):
            alert = Alert(
                market_id=f"market{i}",
                title=f"Market {i}",
                message=f"Alert {i}",
                level=AlertLevel.INFO,
            )
            with patch('sys.stdout.write'):
                manager.dispatch_alert(alert)
        
        manager.clear_history()
        
        assert len(manager.alert_history) == 0
    
    def test_custom_alert_rule(self, manager):
        """Test adding custom alert rule"""
        def condition(shift_data):
            return shift_data.get("custom_metric", 0) > 100
        
        def create_alert(shift_data):
            return Alert(
                market_id=shift_data["market_id"],
                title="Custom Alert",
                message="Custom metric exceeded",
                level=AlertLevel.WARNING,
            )
        
        manager.add_rule("custom_rule", condition, create_alert)
        
        assert len(manager.rules) == 1
        assert manager.rules[0]["name"] == "custom_rule"

