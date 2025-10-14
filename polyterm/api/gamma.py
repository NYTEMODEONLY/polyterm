"""Gamma Markets REST API client"""

import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    from dateutil import parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class RateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)
        
        self.last_request_time = time.time()


class GammaClient:
    """Client for Gamma Markets REST API"""
    
    def __init__(self, base_url: str = "https://gamma-api.polymarket.com", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.rate_limiter = RateLimiter(requests_per_minute=60)
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make rate-limited request to API"""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")
    
    def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: Optional[bool] = None,
        closed: Optional[bool] = None,
        tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of markets (uses /events endpoint for current data)
        
        Args:
            limit: Maximum number of markets to return
            offset: Offset for pagination
            active: Filter for active markets (default: True for live data)
            closed: Filter for closed markets (default: False for live data)
            tag: Filter by tag (e.g., 'politics', 'crypto', 'sports')
        
        Returns:
            List of market dictionaries with live data
        """
        # Default to active, non-closed markets for live data
        if active is None:
            active = True
        if closed is None:
            closed = False
            
        params = {"limit": limit, "offset": offset}
        
        if active is not None:
            params["active"] = str(active).lower()
        if closed is not None:
            params["closed"] = str(closed).lower()
        if tag:
            params["tag"] = tag
        
        # Use /events endpoint which returns current data with volume
        return self._request("GET", "/events", params=params)
    
    def get_market(self, market_id: str) -> Dict[str, Any]:
        """Get single market details
        
        Args:
            market_id: Market ID or slug
        
        Returns:
            Market dictionary with full details
        """
        return self._request("GET", f"/markets/{market_id}")
    
    def get_market_prices(self, market_id: str) -> Dict[str, Any]:
        """Get current prices for a market
        
        Args:
            market_id: Market ID
        
        Returns:
            Dictionary with current prices and probabilities
        """
        return self._request("GET", f"/markets/{market_id}/prices")
    
    def get_market_volume(self, market_id: str, interval: str = "1h") -> List[Dict[str, Any]]:
        """Get volume data for a market
        
        Args:
            market_id: Market ID
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d)
        
        Returns:
            List of volume data points
        """
        params = {"interval": interval}
        return self._request("GET", f"/markets/{market_id}/volume", params=params)
    
    def get_market_trades(
        self,
        market_id: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent trades for a market
        
        Args:
            market_id: Market ID
            limit: Maximum number of trades
            before: Unix timestamp to get trades before
        
        Returns:
            List of trade dictionaries
        """
        params = {"limit": limit}
        if before:
            params["before"] = before
        
        return self._request("GET", f"/markets/{market_id}/trades", params=params)
    
    def search_markets(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for markets by query
        
        Args:
            query: Search query string
            limit: Maximum number of results
        
        Returns:
            List of matching markets
        """
        params = {"q": query, "limit": limit}
        return self._request("GET", "/markets/search", params=params)
    
    def get_trending_markets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending markets by volume
        
        Args:
            limit: Maximum number of markets
        
        Returns:
            List of trending market dictionaries
        """
        params = {"limit": limit}
        return self._request("GET", "/markets/trending", params=params)
    
    def get_market_liquidity(self, market_id: str) -> Dict[str, Any]:
        """Get liquidity information for a market
        
        Args:
            market_id: Market ID
        
        Returns:
            Dictionary with liquidity data
        """
        return self._request("GET", f"/markets/{market_id}/liquidity")
    
    def is_market_fresh(self, market: Dict[str, Any], max_age_hours: int = 24) -> bool:
        """Check if market data is fresh (not stale)
        
        Args:
            market: Market dictionary
            max_age_hours: Maximum age in hours to consider fresh
        
        Returns:
            True if market is fresh, False if stale
        """
        try:
            # Check end date
            end_date_str = market.get('endDate', market.get('end_date_iso', ''))
            if not end_date_str:
                return False
            
            # Parse ISO date
            if HAS_DATEUTIL:
                end_date = parser.parse(end_date_str)
            else:
                # Simple ISO date parsing for YYYY-MM-DD format
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            
            now = datetime.now(end_date.tzinfo) if end_date.tzinfo else datetime.now()
            
            # Market should end in the future or very recently (within max_age_hours)
            if end_date < now - timedelta(hours=max_age_hours):
                return False
            
            # Check if market is from current year or future
            if end_date.year < datetime.now().year:
                return False
                
            return True
        except Exception:
            # If we can't parse date, consider it stale
            return False
    
    def filter_fresh_markets(
        self,
        markets: List[Dict[str, Any]],
        max_age_hours: int = 24,
        require_volume: bool = True,
        min_volume: float = 0.01
    ) -> List[Dict[str, Any]]:
        """Filter markets to only include fresh, active ones
        
        Args:
            markets: List of markets
            max_age_hours: Maximum age to consider fresh
            require_volume: Require markets to have volume data
            min_volume: Minimum volume threshold
        
        Returns:
            Filtered list of fresh markets
        """
        fresh_markets = []
        
        for market in markets:
            # Check freshness
            if not self.is_market_fresh(market, max_age_hours):
                continue
            
            # Check if closed
            if market.get('closed', False):
                continue
            
            # Check volume if required
            if require_volume:
                volume = float(market.get('volume', 0) or 0)
                volume_24hr = float(market.get('volume24hr', 0) or 0)
                
                if volume < min_volume and volume_24hr < min_volume:
                    continue
            
            fresh_markets.append(market)
        
        return fresh_markets
    
    def close(self):
        """Close the session"""
        self.session.close()

