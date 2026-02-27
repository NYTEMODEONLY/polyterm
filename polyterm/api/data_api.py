"""Data API client for Polymarket wallet data"""

import json
import requests
from typing import Dict, List, Optional, Any


class DataAPIClient:
    """Client for Polymarket Data API — real wallet positions, activity, trades"""

    BASE_URL = "https://data-api.polymarket.com"

    def __init__(self, base_url=None):
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.session = requests.Session()

    def _request(self, method, endpoint, retries=3, **kwargs):
        """Make request with retry logic and backoff (same pattern as CLOBClient)"""
        import time as _time
        kwargs.setdefault('timeout', 15)
        url = f"{self.base_url}{endpoint}"

        for attempt in range(retries):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 429:
                    wait = min(2 ** attempt * 2, 30)
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            wait = min(int(retry_after), 60)
                        except (ValueError, TypeError):
                            pass
                    _time.sleep(wait)
                    continue
                if response.status_code >= 500 and attempt < retries - 1:
                    _time.sleep(2 ** attempt)
                    continue
                return response
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    _time.sleep(2 ** attempt)
                    continue
                raise
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    _time.sleep(2 ** attempt)
                    continue
                raise
        raise Exception(f"API request failed after {retries} retries: {url}")

    def get_positions(self, address, limit=100, offset=0, sort_by="CURRENT_VALUE"):
        """Get wallet positions
        GET /positions?user={address}&limit={limit}&offset={offset}&sortBy={sort_by}
        Returns list of position dicts
        """
        params = {"user": address, "limit": limit, "offset": offset, "sortBy": sort_by}
        response = self._request("GET", "/positions", params=params)
        response.raise_for_status()
        return response.json()

    def get_activity(self, address, limit=100, offset=0):
        """Get wallet activity
        GET /activity?user={address}&limit={limit}&offset={offset}
        Returns list of activity items
        """
        params = {"user": address, "limit": limit, "offset": offset}
        response = self._request("GET", "/activity", params=params)
        response.raise_for_status()
        return response.json()

    def get_trades(self, address, limit=100, market=None):
        """Get wallet trades
        GET /trades?user={address}&limit={limit}&market={market}
        Returns list of trade dicts
        """
        params = {"user": address, "limit": limit}
        if market:
            params["market"] = market
        response = self._request("GET", "/trades", params=params)
        response.raise_for_status()
        return response.json()

    def get_profit_summary(self, address):
        """Get profit/loss summary for a wallet by aggregating positions sorted by PNL
        GET /positions?user={address}&sortBy=PNL
        Returns dict with total_pnl, total_invested, position_count
        """
        response = self._request("GET", "/positions", params={"user": address, "sortBy": "PNL", "limit": 500})
        response.raise_for_status()
        positions = response.json()

        if not isinstance(positions, list):
            positions = []

        total_pnl = 0.0
        total_invested = 0.0
        for pos in positions:
            try:
                total_pnl += float(pos.get("pnl", 0) or 0)
                total_invested += float(pos.get("initialValue", 0) or 0)
            except (ValueError, TypeError):
                continue

        return {
            "total_pnl": total_pnl,
            "total_invested": total_invested,
            "position_count": len(positions),
            "positions": positions,
        }

    def close(self):
        """Close the session"""
        self.session.close()
