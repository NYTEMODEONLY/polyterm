"""Configuration management for PolyTerm"""

import os
import toml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Manages PolyTerm configuration"""
    
    DEFAULT_CONFIG = {
        "alerts": {
            "probability_threshold": 10.0,
            "volume_threshold": 50.0,
            "check_interval": 60,
        },
        "api": {
            "gamma_api_key": "",
            "gamma_base_url": "https://gamma-api.polymarket.com",
            "gamma_markets_endpoint": "/events",  # Use /events for live data with volume
            "clob_endpoint": "wss://ws-live-data.polymarket.com",
            "clob_rest_endpoint": "https://clob.polymarket.com",
            "subgraph_endpoint": "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets",
            "kalshi_api_key": "",
            "kalshi_base_url": "https://trading-api.kalshi.com/trade-api/v2",
        },
        "wallet": {
            "address": "",
            "tracked_wallets": [],
        },
        "display": {
            "use_colors": True,
            "max_markets": 20,
            "refresh_rate": 2,
        },
        "data_validation": {
            "max_market_age_hours": 24,
            "require_volume_data": True,
            "min_volume_threshold": 0.01,
            "reject_closed_markets": True,
            "enable_api_fallback": True,
        },
        "notifications": {
            "desktop": True,
            "sound": False,
            "webhook": False,
            "webhook_url": "",
            "quiet_hours_start": "",
            "quiet_hours_end": "",
            "min_change": 5,
            "min_volume": 1000,
            "telegram": {
                "enabled": False,
                "bot_token": "",
                "chat_id": "",
            },
            "discord": {
                "enabled": False,
                "webhook_url": "",
            },
            "system": {
                "enabled": True,
            },
            "sound_file": {
                "enabled": True,
                "file": "",
            },
            "email": {
                "enabled": False,
                "smtp_host": "",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": "",
                "email_to": "",
            },
        },
        "whale_tracking": {
            "min_whale_trade": 10000,
            "min_smart_money_win_rate": 0.70,
            "min_smart_money_trades": 10,
            "insider_alert_threshold": 70,
        },
        "arbitrage": {
            "min_spread": 0.025,  # 2.5% minimum profitable spread
            "include_kalshi": False,
            "polymarket_fee": 0.02,  # 2% winner fee
            "kalshi_fee": 0.007,  # 0.7% fee
        },
    }
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path.home() / ".polyterm" / "config.toml"
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    user_config = toml.load(f)
                # Merge with defaults
                config = self.DEFAULT_CONFIG.copy()
                self._deep_merge(config, user_config)
                return config
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            return self.DEFAULT_CONFIG.copy()
    
    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """Deep merge update dict into base dict"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save(self) -> None:
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            toml.dump(self.config, f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'alerts.probability_threshold')"""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    # Validation rules: key -> (type, min, max)
    VALIDATION_RULES = {
        "alerts.probability_threshold": (float, 0.1, 100.0),
        "alerts.volume_threshold": (float, 0.0, 10000.0),
        "alerts.check_interval": (int, 5, 3600),
        "display.max_markets": (int, 1, 200),
        "display.refresh_rate": (int, 1, 60),
        "whale_tracking.min_whale_trade": (float, 100, 10000000),
        "whale_tracking.min_smart_money_win_rate": (float, 0.0, 1.0),
        "whale_tracking.min_smart_money_trades": (int, 1, 10000),
        "whale_tracking.insider_alert_threshold": (int, 0, 100),
        "arbitrage.min_spread": (float, 0.001, 1.0),
        "arbitrage.polymarket_fee": (float, 0.0, 0.5),
        "arbitrage.kalshi_fee": (float, 0.0, 0.5),
        "data_validation.max_market_age_hours": (int, 1, 720),
        "data_validation.min_volume_threshold": (float, 0.0, 1000000),
    }

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation with validation"""
        # Validate if rules exist for this key
        if key in self.VALIDATION_RULES:
            expected_type, min_val, max_val = self.VALIDATION_RULES[key]
            try:
                value = expected_type(value)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid type for {key}: expected {expected_type.__name__}")
            if value < min_val or value > max_val:
                raise ValueError(f"Value for {key} must be between {min_val} and {max_val}")

        keys = key.split(".")
        config = self.config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    @property
    def gamma_api_key(self) -> str:
        return self.get("api.gamma_api_key", "")
    
    @property
    def gamma_base_url(self) -> str:
        return self.get("api.gamma_base_url", "https://gamma-api.polymarket.com")
    
    @property
    def gamma_markets_endpoint(self) -> str:
        return self.get("api.gamma_markets_endpoint", "/events")
    
    @property
    def clob_endpoint(self) -> str:
        return self.get("api.clob_endpoint", "wss://ws-live-data.polymarket.com")
    
    @property
    def clob_rest_endpoint(self) -> str:
        return self.get("api.clob_rest_endpoint", "https://clob.polymarket.com")
    
    @property
    def subgraph_endpoint(self) -> str:
        return self.get("api.subgraph_endpoint", "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets")
    
    @property
    def probability_threshold(self) -> float:
        return self.get("alerts.probability_threshold", 10.0)
    
    @property
    def volume_threshold(self) -> float:
        return self.get("alerts.volume_threshold", 50.0)
    
    @property
    def check_interval(self) -> int:
        return self.get("alerts.check_interval", 60)
    
    @property
    def wallet_address(self) -> str:
        return self.get("wallet.address", "")

    @property
    def kalshi_api_key(self) -> str:
        return self.get("api.kalshi_api_key", "")

    @property
    def kalshi_base_url(self) -> str:
        return self.get("api.kalshi_base_url", "https://trading-api.kalshi.com/trade-api/v2")

    @property
    def notification_config(self) -> dict:
        """Get notification configuration"""
        return self.get("notifications", {})

    @property
    def whale_tracking_config(self) -> dict:
        """Get whale tracking configuration"""
        return self.get("whale_tracking", {})

    @property
    def arbitrage_config(self) -> dict:
        """Get arbitrage configuration"""
        return self.get("arbitrage", {})

    def get_tracked_wallets(self) -> list:
        """Get list of tracked wallet addresses"""
        return self.get("wallet.tracked_wallets", [])

    def add_tracked_wallet(self, address: str) -> None:
        """Add wallet to tracked list"""
        wallets = self.get_tracked_wallets()
        if address not in wallets:
            wallets.append(address)
            self.set("wallet.tracked_wallets", wallets)

    def remove_tracked_wallet(self, address: str) -> None:
        """Remove wallet from tracked list"""
        wallets = self.get_tracked_wallets()
        if address in wallets:
            wallets.remove(address)
            self.set("wallet.tracked_wallets", wallets)

