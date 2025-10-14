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
            "clob_endpoint": "wss://clob.polymarket.com/ws",
            "clob_rest_endpoint": "https://clob.polymarket.com",
            "subgraph_endpoint": "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets",
        },
        "wallet": {
            "address": "",
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
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split(".")
        config = self.config
        for k in keys[:-1]:
            if k not in config:
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
    def clob_endpoint(self) -> str:
        return self.get("api.clob_endpoint", "wss://clob.polymarket.com/ws")
    
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

