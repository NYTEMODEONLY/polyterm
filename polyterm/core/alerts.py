"""Alert system for market shifts"""

import sys
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert:
    """Alert data structure"""
    
    def __init__(
        self,
        market_id: str,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        data: Optional[Dict[str, Any]] = None,
    ):
        self.market_id = market_id
        self.title = title
        self.message = message
        self.level = level
        self.data = data or {}
        self.timestamp = datetime.now()
    
    def __str__(self):
        return f"[{self.level.value.upper()}] {self.title}: {self.message}"


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, enable_system_notifications: bool = False):
        self.enable_system_notifications = enable_system_notifications and HAS_PLYER
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        # Alert callbacks
        self.callbacks: List[Callable[[Alert], None]] = []
        
        # Alert rules
        self.rules: List[Dict[str, Any]] = []
    
    def add_callback(self, callback: Callable[[Alert], None]):
        """Add alert callback"""
        self.callbacks.append(callback)
    
    def add_rule(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], bool],
        create_alert: Callable[[Dict[str, Any]], Alert],
    ):
        """Add custom alert rule
        
        Args:
            name: Rule name
            condition: Function that returns True if alert should trigger
            create_alert: Function that creates Alert from shift data
        """
        self.rules.append({
            "name": name,
            "condition": condition,
            "create_alert": create_alert,
        })
    
    def create_probability_shift_alert(
        self,
        shift_data: Dict[str, Any],
        threshold: float = 10.0,
    ) -> Optional[Alert]:
        """Create alert for probability shift"""
        changes = shift_data.get("changes", {})
        prob_change = changes.get("probability_change", 0)
        
        if abs(prob_change) < threshold:
            return None
        
        direction = "increased" if prob_change > 0 else "decreased"
        level = AlertLevel.CRITICAL if abs(prob_change) >= 20 else AlertLevel.WARNING
        
        message = f"Probability {direction} by {abs(prob_change):.1f}%"
        
        return Alert(
            market_id=shift_data["market_id"],
            title=shift_data.get("title", "Unknown Market"),
            message=message,
            level=level,
            data=shift_data,
        )
    
    def create_volume_spike_alert(
        self,
        shift_data: Dict[str, Any],
        threshold: float = 50.0,
    ) -> Optional[Alert]:
        """Create alert for volume spike"""
        changes = shift_data.get("changes", {})
        vol_change = changes.get("volume_change", 0)
        
        if abs(vol_change) < threshold:
            return None
        
        direction = "spiked" if vol_change > 0 else "dropped"
        level = AlertLevel.WARNING if abs(vol_change) >= 100 else AlertLevel.INFO
        
        message = f"Volume {direction} by {abs(vol_change):.1f}%"
        
        return Alert(
            market_id=shift_data["market_id"],
            title=shift_data.get("title", "Unknown Market"),
            message=message,
            level=level,
            data=shift_data,
        )
    
    def create_liquidity_alert(
        self,
        shift_data: Dict[str, Any],
        threshold: float = 30.0,
    ) -> Optional[Alert]:
        """Create alert for liquidity change"""
        changes = shift_data.get("changes", {})
        liq_change = changes.get("liquidity_change", 0)
        
        if abs(liq_change) < threshold:
            return None
        
        direction = "increased" if liq_change > 0 else "decreased"
        level = AlertLevel.WARNING if liq_change < -30 else AlertLevel.INFO
        
        message = f"Liquidity {direction} by {abs(liq_change):.1f}%"
        
        return Alert(
            market_id=shift_data["market_id"],
            title=shift_data.get("title", "Unknown Market"),
            message=message,
            level=level,
            data=shift_data,
        )
    
    def process_shift(self, shift_data: Dict[str, Any], thresholds: Dict[str, float]):
        """Process shift data and generate appropriate alerts"""
        alerts = []
        
        # Check built-in alert types
        prob_alert = self.create_probability_shift_alert(
            shift_data,
            threshold=thresholds.get("probability", 10.0),
        )
        if prob_alert:
            alerts.append(prob_alert)
        
        vol_alert = self.create_volume_spike_alert(
            shift_data,
            threshold=thresholds.get("volume", 50.0),
        )
        if vol_alert:
            alerts.append(vol_alert)
        
        liq_alert = self.create_liquidity_alert(
            shift_data,
            threshold=thresholds.get("liquidity", 30.0),
        )
        if liq_alert:
            alerts.append(liq_alert)
        
        # Check custom rules
        for rule in self.rules:
            try:
                if rule["condition"](shift_data):
                    alert = rule["create_alert"](shift_data)
                    if alert:
                        alerts.append(alert)
            except Exception as e:
                print(f"Error processing rule {rule['name']}: {e}")
        
        # Dispatch alerts
        for alert in alerts:
            self.dispatch_alert(alert)
    
    def dispatch_alert(self, alert: Alert):
        """Dispatch alert to all channels"""
        # Store in history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        # Terminal output
        self._print_terminal_alert(alert)
        
        # System notification
        if self.enable_system_notifications:
            self._send_system_notification(alert)
        
        # Call callbacks
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")
    
    def _print_terminal_alert(self, alert: Alert):
        """Print alert to terminal with formatting"""
        # Terminal bell for critical alerts
        if alert.level == AlertLevel.CRITICAL:
            sys.stdout.write("\a")
            sys.stdout.flush()
        
        # Color codes
        colors = {
            AlertLevel.INFO: "\033[94m",      # Blue
            AlertLevel.WARNING: "\033[93m",   # Yellow
            AlertLevel.CRITICAL: "\033[91m",  # Red
        }
        reset = "\033[0m"
        
        color = colors.get(alert.level, "")
        timestamp = alert.timestamp.strftime("%H:%M:%S")
        
        print(f"{color}[{timestamp}] {alert}{reset}")
    
    def _send_system_notification(self, alert: Alert):
        """Send system notification"""
        if not self.enable_system_notifications:
            return
        
        try:
            notification.notify(
                title=f"PolyTerm Alert: {alert.title[:50]}",
                message=alert.message,
                app_name="PolyTerm",
                timeout=10,
            )
        except Exception as e:
            print(f"Failed to send system notification: {e}")
    
    def get_recent_alerts(self, count: int = 10) -> List[Alert]:
        """Get most recent alerts"""
        return self.alert_history[-count:]
    
    def get_alerts_for_market(self, market_id: str) -> List[Alert]:
        """Get all alerts for a specific market"""
        return [a for a in self.alert_history if a.market_id == market_id]
    
    def clear_history(self):
        """Clear alert history"""
        self.alert_history.clear()

