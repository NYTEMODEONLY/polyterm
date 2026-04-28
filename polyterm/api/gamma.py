"""Gamma Markets REST API client"""

import json
import os
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    from dateutil import parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class RateLimiter:
    """Simple per-process rate limiter for API requests"""

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


class SharedRateLimiter:
    """Cross-process rate limiter using file-based coordination.

    Uses a lockfile at ``~/.polyterm/gamma_rate.lock`` (configurable) to
    coordinate Gamma API request timing across concurrent PolyTerm processes.
    Falls back to a per-process ``RateLimiter`` when file locking is
    unavailable (e.g. Windows or permission errors).
    """

    # Timestamps older than this (seconds) are treated as stale and ignored.
    _STALE_THRESHOLD = 120.0

    def __init__(
        self,
        requests_per_minute: int = 60,
        lock_dir: Optional[str] = None,
    ):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self._lock_dir = Path(lock_dir) if lock_dir else Path.home() / ".polyterm"
        self._lock_file = self._lock_dir / "gamma_rate.lock"
        self._fallback = RateLimiter(requests_per_minute)
        self._shared_available = self._init_shared()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_shared(self) -> bool:
        """Return True if cross-process locking is available."""
        try:
            import fcntl  # noqa: F401 – availability check
            self._lock_dir.mkdir(parents=True, exist_ok=True)
            return True
        except (ImportError, OSError):
            return False

    # ------------------------------------------------------------------
    # Public API (same interface as RateLimiter)
    # ------------------------------------------------------------------

    def wait_if_needed(self):
        """Wait if necessary to respect the *global* rate limit.

        If the shared lock mechanism is available the wait is coordinated
        across all PolyTerm processes.  Otherwise falls back to per-process
        limiting so single-process usage is unaffected.
        """
        if not self._shared_available:
            self._fallback.wait_if_needed()
            return

        try:
            self._shared_wait()
        except Exception:
            # Any unexpected error → degrade gracefully to per-process.
            self._fallback.wait_if_needed()

    # ------------------------------------------------------------------
    # Internal – file-based coordination
    # ------------------------------------------------------------------

    def _shared_wait(self):
        import fcntl

        self._lock_dir.mkdir(parents=True, exist_ok=True)

        # Open (or create) the lock file and acquire an exclusive lock.
        fd = os.open(str(self._lock_file), os.O_RDWR | os.O_CREAT)
        try:
            f = os.fdopen(fd, "r+")
        except Exception:
            os.close(fd)
            raise

        try:
            fcntl.flock(f, fcntl.LOCK_EX)

            # --- critical section (lock held) ---
            f.seek(0)
            content = f.read().strip()

            last_request_time = 0.0
            if content:
                try:
                    last_request_time = float(content)
                except (ValueError, TypeError):
                    last_request_time = 0.0

            current_time = time.time()

            # Discard stale timestamps (e.g. from a crashed process).
            if current_time - last_request_time > self._STALE_THRESHOLD:
                last_request_time = 0.0

            next_allowed = last_request_time + self.min_interval
            my_slot = max(current_time, next_allowed)

            # Reserve this slot for the current process.
            f.seek(0)
            f.truncate()
            f.write(str(my_slot))
            f.flush()
            # --- end critical section ---
        finally:
            # Release the lock and close the file.
            try:
                fcntl.flock(f, fcntl.LOCK_UN)
            except Exception:
                pass
            f.close()

        # Sleep *outside* the lock so other processes can reserve their slots.
        wait_time = my_slot - time.time()
        if wait_time > 0:
            time.sleep(wait_time)


class GammaClient:
    """Client for Gamma Markets REST API"""
    
    def __init__(self, base_url: str = "https://gamma-api.polymarket.com", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.rate_limiter = SharedRateLimiter(requests_per_minute=60)
        self.session = requests.Session()
        self._search_endpoint_supported = True
        self._markets_keyset_supported = True
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def _request(self, method: str, endpoint: str, retries: int = 3, **kwargs) -> Dict[str, Any]:
        """Make rate-limited request to API with retry logic"""
        self.rate_limiter.wait_if_needed()

        url = f"{self.base_url}{endpoint}"

        for attempt in range(retries):
            try:
                response = self.session.request(method, url, timeout=15, **kwargs)

                # Handle rate limiting with exponential backoff
                if response.status_code == 429:
                    wait_time = min(2 ** attempt * 2, 30)
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            wait_time = min(int(retry_after), 60)
                        except (ValueError, TypeError):
                            pass  # Keep default exponential backoff
                    import time
                    time.sleep(wait_time)
                    continue

                # Retry on server errors
                if response.status_code >= 500 and attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue

                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"API request timed out after {retries} attempts: {url}")
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"Connection failed after {retries} attempts: {url}")
            except requests.exceptions.RequestException as e:
                raise Exception(f"API request failed: {e}")

        raise Exception(f"API request failed after {retries} attempts: {url}")
    
    def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: Optional[bool] = None,
        closed: Optional[bool] = None,
        tag: Optional[str] = None,
        market_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of markets using Gamma keyset pagination.

        Args:
            limit: Maximum number of markets to return
            offset: Compatibility offset. Gamma keyset rejects offset, so this
                is emulated client-side by fetching and slicing.
            active: Filter for active markets (default: True for live data)
            closed: Filter for closed markets (default: False for live data)
            tag: Filter by tag (e.g., 'politics', 'crypto', 'sports')
            market_id: Compatibility filter for older callers that used
                get_markets(limit=1, market_id=...)

        Returns:
            List of market dictionaries with live data
        """
        if market_id:
            return self._get_market_as_list(market_id)

        # Default to active, non-closed markets for live data
        if active is None:
            active = True
        if closed is None:
            closed = False

        params: Dict[str, Any] = {}
        if active is not None:
            params["active"] = str(active).lower()
        if closed is not None:
            params["closed"] = str(closed).lower()
        if tag:
            params["tag"] = tag

        if self._markets_keyset_supported:
            try:
                return self._get_markets_keyset(limit=limit, offset=offset, params=params)
            except Exception as exc:
                err = str(exc)
                if "422 Client Error" in err or "404 Client Error" in err or " 422 " in err or " 404 " in err:
                    self._markets_keyset_supported = False
                else:
                    raise

        legacy_params = params.copy()
        legacy_params["limit"] = limit
        if offset:
            legacy_params["offset"] = offset
        return self._request("GET", "/markets", params=legacy_params)

    def _get_market_as_list(self, market_id: str) -> List[Dict[str, Any]]:
        """Return a single market as a list for legacy get_markets callers."""
        try:
            market = self.get_market(market_id)
            return [market] if market else []
        except Exception:
            return []

    def _get_markets_keyset(
        self,
        limit: int,
        offset: int,
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fetch markets from /markets/keyset and preserve the old list return."""
        target_count = max(limit + max(offset, 0), limit, 1)
        collected: List[Dict[str, Any]] = []
        after_cursor = None

        while len(collected) < target_count:
            page_params = params.copy()
            page_params["limit"] = min(target_count - len(collected), 1000)
            if after_cursor:
                page_params["after_cursor"] = after_cursor

            data = self._request("GET", "/markets/keyset", params=page_params)
            page_markets = self._extract_markets_page(data)
            collected.extend(page_markets)

            after_cursor = data.get("next_cursor") if isinstance(data, dict) else None
            if not after_cursor or not page_markets:
                break

        return collected[offset:offset + limit]

    @staticmethod
    def _extract_markets_page(data: Any) -> List[Dict[str, Any]]:
        """Normalize Gamma list responses from keyset or legacy endpoints."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            markets = data.get("markets", data.get("data", []))
            return markets if isinstance(markets, list) else []
        return []
    
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
        # Try search endpoint first when supported.
        # Gamma currently returns 422 for this endpoint in some environments.
        if self._search_endpoint_supported:
            try:
                params = {"q": query, "limit": limit}
                results = self._request("GET", "/markets/search", params=params)
                if results:
                    return results
            except Exception as exc:
                err = str(exc)
                if "422 Client Error" in err or "404 Client Error" in err or " 422 " in err or " 404 " in err:
                    self._search_endpoint_supported = False

        # Fallback: get markets and filter locally
        try:
            markets = self.get_markets(limit=200)
            query_lower = query.lower()

            matches = []
            for market in markets:
                title = market.get('question', market.get('title', '')).lower()
                if query_lower in title:
                    matches.append(market)
                    if len(matches) >= limit:
                        break

            return matches
        except Exception:
            return []
    
    def get_trending_markets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending markets by 24hr volume
        
        Args:
            limit: Maximum number of markets
        
        Returns:
            List of trending market dictionaries sorted by 24hr volume
        """
        params = {
            "active": "true",
            "closed": "false",
            "order": "volume24hr",
            "ascending": "false",
        }
        return self._get_markets_keyset(limit=limit, offset=0, params=params)
    
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
        # Primary check: use active/closed flags from API
        # These are authoritative - if a market is marked active and not closed, it's tradeable
        is_active = market.get('active')
        is_closed = market.get('closed')

        # If we have explicit active/closed flags, use them
        if is_active is not None and is_closed is not None:
            return is_active and not is_closed

        # Fallback: check end date for markets without explicit flags
        try:
            end_date_str = market.get('endDate', market.get('end_date_iso', ''))
            if not end_date_str:
                # No date info - check if market has active flag as fallback
                # Perpetual/open-ended markets may not have end dates
                if is_active is not None:
                    return bool(is_active)
                return False

            # Parse ISO date
            if HAS_DATEUTIL:
                end_date = parser.parse(end_date_str)
            else:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))

            now = datetime.now(end_date.tzinfo) if end_date.tzinfo else datetime.now()

            # Market should end in the future or very recently (within max_age_hours)
            if end_date < now - timedelta(hours=max_age_hours):
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
    
    def get_resolution(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get resolution/settlement data for a market.

        Args:
            market_id: Market ID or condition ID

        Returns:
            Resolution data dict with keys: resolved, outcome, winning_price,
            resolved_at, resolution_source, closed_at, status.
            Returns None if market not found.
        """
        try:
            market = self.get_market(market_id)
        except Exception:
            return None

        if not market:
            return None

        return self._parse_resolution(market)

    def get_resolved_markets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently resolved markets.

        Args:
            limit: Maximum number of markets to return

        Returns:
            List of market dicts with resolution data attached
        """
        params = {
            "limit": limit,
            "closed": "true",
            "order": "endDate",
            "ascending": "false",
        }

        try:
            markets = self._request("GET", "/markets", params=params)
        except Exception:
            return []

        results = []
        for market in markets:
            resolution = self._parse_resolution(market)
            if resolution and resolution.get('resolved'):
                market['_resolution'] = resolution
                results.append(market)

        return results

    def _parse_resolution(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """Parse resolution data from a market response.

        Determines resolution status from closed/active flags and outcomePrices.
        A market is considered resolved when it is closed and outcomePrices
        show a definitive outcome (one side at 1.0).

        Args:
            market: Raw market dict from Gamma API

        Returns:
            Resolution data dict
        """
        is_closed = bool(market.get('closed', False))
        is_active = bool(market.get('active', True))

        # Parse outcome prices
        outcome_prices = market.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except (json.JSONDecodeError, TypeError):
                outcome_prices = []

        # Convert to floats
        try:
            outcome_prices = [float(p) for p in outcome_prices]
        except (ValueError, TypeError):
            outcome_prices = []

        # Parse timestamps
        closed_at = None
        end_date_str = market.get('endDate', '')
        if end_date_str:
            try:
                closed_at = datetime.fromisoformat(
                    end_date_str.replace('Z', '+00:00')
                ).replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        resolution_source = market.get('resolvedBy', '')

        # Determine resolution outcome
        resolved = False
        outcome = ""
        winning_price = 0.0

        if is_closed and outcome_prices:
            # Check for definitive resolution: one side at ~1.0, other at ~0.0
            if len(outcome_prices) >= 2:
                yes_price = outcome_prices[0]
                no_price = outcome_prices[1]

                if yes_price >= 0.95:
                    resolved = True
                    outcome = "YES"
                    winning_price = yes_price
                elif no_price >= 0.95:
                    resolved = True
                    outcome = "NO"
                    winning_price = no_price

        # Status string
        if resolved:
            status = f"Resolved: {outcome}"
        elif is_closed and not is_active:
            status = "Pending resolution"
        elif is_closed:
            status = "Closed"
        else:
            status = "Active"

        return {
            'market_id': market.get('id', market.get('condition_id', '')),
            'market_slug': market.get('slug', ''),
            'title': market.get('question', market.get('title', '')),
            'resolved': resolved,
            'outcome': outcome,
            'winning_price': winning_price,
            'resolved_at': closed_at if resolved else None,
            'closed_at': closed_at,
            'resolution_source': resolution_source,
            'status': status,
        }

    def close(self):
        """Close the session"""
        self.session.close()
