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
                if response.status_code == 408 and attempt < retries - 1:
                    _time.sleep(2 ** attempt)
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

    def get_positions(self, address, limit=100, offset=0, sort_by="CURRENT"):
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

    def get_trades(self, address=None, limit=100, market=None, before=None):
        """Get wallet trades
        GET /trades?user={address}&limit={limit}&market={market}
        Returns list of trade dicts
        """
        params = {"limit": limit}
        if address:
            params["user"] = address
        if market:
            params["market"] = market
        if before:
            params["before"] = before
        response = self._request("GET", "/trades", params=params)
        response.raise_for_status()
        return response.json()

    def get_recent_trades(self, limit=1000, offset=0, filter_type=None, filter_amount=None, taker_only=True):
        """Get recent public trades from the global Data API trade tape.

        `filterType=CASH&filterAmount=N` asks the Data API for trades whose
        cash notional is at least N. The public API currently caps pages at
        1,000 rows and rejects offsets above 3,000. Callers that scan time
        windows should expose that limit in quality flags instead of pretending
        the whole chain history was read.
        """
        params = {"limit": limit, "offset": offset, "takerOnly": str(taker_only).lower()}
        if filter_type and filter_amount is not None:
            params["filterType"] = filter_type
            params["filterAmount"] = filter_amount
        response = self._request("GET", "/trades", params=params)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    def get_holders(self, market=None, token_id=None, limit=100, offset=0):
        """Get holders for a market or token when the public endpoint supports it."""
        params = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market
        if token_id:
            params["token"] = token_id
        response = self._request("GET", "/holders", params=params)
        response.raise_for_status()
        return response.json()

    def get_value(self, address):
        """Get account value for a wallet when available from the Data API."""
        response = self._request("GET", "/value", params={"user": address})
        response.raise_for_status()
        return response.json()

    def get_market_positions(self, market, limit=100, offset=0):
        """Get current user positions for a specific market when available."""
        params = {"market": market, "limit": limit, "offset": offset}
        response = self._request("GET", "/positions", params=params)
        response.raise_for_status()
        return response.json()

    def get_closed_positions(self, address, limit=50, offset=0, sort_by="REALIZEDPNL"):
        """Get closed positions for a wallet.

        GET /closed-positions?user={address}&limit={limit}&offset={offset}&sortBy={sort_by}
        Returns list of closed position dicts when the public Data API surface is available.
        """
        params = {"user": address, "limit": limit, "offset": offset, "sortBy": sort_by}
        response = self._request("GET", "/closed-positions", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data.get("data", data.get("positions", []))
        return data

    def get_leaderboard(self, period="7d", limit=50, sort_by="profit"):
        """Get public leaderboard rows if exposed by the current Data API.

        The public Data API has changed this surface more often than positions
        and trades, so callers should handle an empty list or request error.
        """
        period_map = {
            "24h": "DAY",
            "1d": "DAY",
            "day": "DAY",
            "7d": "WEEK",
            "week": "WEEK",
            "30d": "MONTH",
            "month": "MONTH",
            "all": "ALL",
        }
        sort_map = {
            "profit": "PNL",
            "pnl": "PNL",
            "volume": "VOL",
            "vol": "VOL",
            "winrate": "PNL",
            "active": "VOL",
        }
        params = {
            "timePeriod": period_map.get(str(period).lower(), str(period).upper()),
            "limit": limit,
            "orderBy": sort_map.get(str(sort_by).lower(), str(sort_by).upper()),
        }
        response = self._request("GET", "/v1/leaderboard", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data.get("data", data.get("leaderboard", data.get("users", [])))
        return data

    def get_wallet_profile(self, address, trades_limit=100, positions_limit=100):
        """Build a wallet profile from public Data API position/trade surfaces."""
        positions = self.get_positions(address, limit=positions_limit)
        trades = self.get_trades(address=address, limit=trades_limit)
        try:
            value = self.get_value(address)
        except Exception:
            value = {}
        return {
            "address": address,
            "positions": positions if isinstance(positions, list) else [],
            "trades": trades if isinstance(trades, list) else [],
            "value": value if isinstance(value, dict) else {},
        }

    def get_profit_summary(self, address):
        """Get profit/loss summary for a wallet by aggregating positions sorted by cash P&L.

        GET /positions?user={address}&sortBy=CASHPNL
        Returns dict with total_pnl, total_invested, position_count
        """
        response = self._request("GET", "/positions", params={"user": address, "sortBy": "CASHPNL", "limit": 500})
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
