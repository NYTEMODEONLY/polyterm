"""CLOB (Central Limit Order Book) API client"""

import asyncio
import json
import logging
import requests
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

try:
    from dateutil import parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class CLOBClient:
    """Client for PolyMarket CLOB API (REST and WebSocket)"""
    
    def __init__(
        self,
        rest_endpoint: str = "https://clob.polymarket.com",
        ws_endpoint: str = "wss://ws-live-data.polymarket.com",
    ):
        self.rest_endpoint = rest_endpoint.rstrip("/")
        self.ws_endpoint = ws_endpoint
        self.session = requests.Session()
        self.ws_connection = None
        self.clob_ws = None
        self.subscriptions = {}
        self._ws_permanently_failed = False

    def _request(self, method: str, url: str, retries: int = 3, **kwargs) -> requests.Response:
        """Make request with retry logic and backoff"""
        import time as _time
        kwargs.setdefault('timeout', 15)

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
                            pass  # Keep default exponential backoff
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

    # REST API Methods

    def get_price_history(
        self,
        token_id: str,
        interval: str = "1h",
        fidelity: int = 60,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get historical prices from CLOB API

        Args:
            token_id: CLOB token ID
            interval: Time interval (max, 1d, 6h, 1h, 1m — maps to start timestamps)
            fidelity: Seconds between data points (60=1min, 3600=1hr)
            start_ts: Unix timestamp start (optional, derived from interval)
            end_ts: Unix timestamp end (optional, defaults to now)

        Returns:
            List of {"t": unix_timestamp, "p": price_string} dicts
        """
        url = f"{self.rest_endpoint}/prices-history"
        params = {"market": token_id, "interval": interval, "fidelity": fidelity}
        if start_ts is not None:
            params["startTs"] = start_ts
        if end_ts is not None:
            params["endTs"] = end_ts

        try:
            response = self._request("GET", url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("history", [])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get price history: {e}")

    def get_order_book(self, token_id: str, depth: int = 20) -> Dict[str, Any]:
        """Get order book for a market

        Args:
            token_id: Token ID (from clobTokenIds field)
            depth: Order book depth (number of price levels)

        Returns:
            Order book with bids and asks
        """
        url = f"{self.rest_endpoint}/book"
        params = {"token_id": token_id}

        try:
            response = self._request("GET", url, params=params)
            response.raise_for_status()
            data = response.json()

            # Limit depth if specified
            if depth and data.get('bids'):
                data['bids'] = data['bids'][:depth]
            if depth and data.get('asks'):
                data['asks'] = data['asks'][:depth]

            return data
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get order book: {e}")
    
    def get_price(self, token_id: str, side: str) -> Dict[str, Any]:
        """Get the current best price for a token and side."""
        url = f"{self.rest_endpoint}/price"
        params = {"token_id": token_id, "side": side.upper()}

        try:
            response = self._request("GET", url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get price: {e}")

    def get_spread(self, token_id: str) -> Dict[str, Any]:
        """Get the current bid/ask spread for a token."""
        url = f"{self.rest_endpoint}/spread"
        params = {"token_id": token_id}

        try:
            response = self._request("GET", url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get spread: {e}")

    def get_last_trade_price(self, token_id: str) -> Dict[str, Any]:
        """Get the last trade price and side for a token."""
        url = f"{self.rest_endpoint}/last-trade-price"
        params = {"token_id": token_id}

        try:
            response = self._request("GET", url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get last trade price: {e}")

    def get_fee_rate(self, token_id: str) -> Dict[str, Any]:
        """Get the current base fee rate for a token."""
        url = f"{self.rest_endpoint}/fee-rate"
        params = {"token_id": token_id}

        try:
            response = self._request("GET", url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get fee rate: {e}")

    def get_ticker(self, token_id: str) -> Dict[str, Any]:
        """Get current lightweight ticker data for a token.

        Kept for compatibility with existing callers. CLOB V2 exposes this
        information through public pricing endpoints instead of the old
        undocumented ``/ticker/{id}`` route.
        """
        ticker: Dict[str, Any] = {}

        try:
            last_trade = self.get_last_trade_price(token_id)
            ticker["last"] = last_trade.get("price", "0")
            ticker["side"] = last_trade.get("side", "")
        except Exception:
            ticker["last"] = "0"
            ticker["side"] = ""

        try:
            spread = self.get_spread(token_id)
            ticker["spread"] = spread.get("spread", "0")
        except Exception:
            ticker["spread"] = "0"

        return ticker

    def get_recent_trades(
        self,
        market_id: str,
        limit: int = 100,
        maker_address: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent authenticated CLOB trades.

        CLOB V2 documents ``GET /trades`` with query parameters. It requires
        auth for user trades, so unauthenticated callers should prefer RTDS
        WebSocket data; this method is retained for REST fallback compatibility.
        """
        url = f"{self.rest_endpoint}/trades"
        params: Dict[str, Any] = {"limit": limit}
        if market_id:
            params["market"] = market_id
        if maker_address:
            params["maker_address"] = maker_address
        if asset_id:
            params["asset_id"] = asset_id

        try:
            response = self._request("GET", url, params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                trades = data.get("data", [])
                return trades if isinstance(trades, list) else []
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get trades: {e}")

    def get_market_depth(self, token_id: str) -> Dict[str, Any]:
        """Get depth statistics from the documented order book endpoint."""
        try:
            book = self.get_order_book(token_id, depth=100)
        except Exception as e:
            raise Exception(f"Failed to get market depth: {e}")

        bid_depth = self._sum_order_notional(book.get("bids", []))
        ask_depth = self._sum_order_notional(book.get("asks", []))
        return {
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "total_depth": bid_depth + ask_depth,
        }

    @staticmethod
    def _sum_order_notional(orders: List[Any]) -> float:
        """Sum price * size for order rows from either CLOB REST shape."""
        total = 0.0
        for order in orders:
            try:
                if isinstance(order, dict):
                    price = float(order.get("price", 0) or 0)
                    size = float(order.get("size", 0) or 0)
                else:
                    price = float(order[0])
                    size = float(order[1])
            except (ValueError, TypeError, IndexError):
                continue
            total += price * size
        return total
    
    # WebSocket Methods for Live Trading Data
    
    async def connect_websocket(self):
        """Connect to PolyMarket RTDS WebSocket"""
        if not HAS_WEBSOCKETS:
            raise Exception("websockets library not installed. Install with: pip install websockets")
        
        try:
            # Connect to RTDS endpoint (no path needed)
            self.ws_connection = await websockets.connect(self.ws_endpoint)
            return True
        except Exception as e:
            raise Exception(f"Failed to connect to WebSocket: {e}")
    
    async def subscribe_to_trades(self, market_slugs: List[str], callback: Callable):
        """Subscribe to live trade feeds for multiple markets using RTDS

        Args:
            market_slugs: List of market slugs to monitor (can be empty to subscribe to all)
            callback: Function to call when trade data is received
        """
        if not self.ws_connection:
            await self.connect_websocket()

        # Subscribe to ALL trades (no filter) - we'll filter client-side
        # This is more reliable than per-market subscriptions which may miss data
        subscribe_msg = {
            "action": "subscribe",
            "subscriptions": [
                {
                    "topic": "activity",
                    "type": "trades"
                }
            ]
        }
        await self.ws_connection.send(json.dumps(subscribe_msg))

        # Store callback for all markets (keyed by slug)
        # Also store a special "_all" key for unfiltered callbacks
        for market_slug in market_slugs:
            self.subscriptions[market_slug] = callback

        # If no specific markets, store callback for all trades
        if not market_slugs:
            self.subscriptions["_all"] = callback
    
    async def listen_for_trades(
        self,
        max_reconnects: int = 5,
        message_timeout: float = 30.0,
        on_error: Optional[Callable[[Exception], None]] = None,
        supervisor_retries: int = 3,
        supervisor_cooldown: float = 60.0,
    ):
        """Listen for incoming trade messages from RTDS with auto-reconnection.

        Features a two-tier resilience model:
        - Inner loop: reconnects up to max_reconnects on connection drops
        - Outer supervisor: restarts the entire connection loop after a cooldown
          when inner reconnects are exhausted

        Args:
            max_reconnects: Max reconnect attempts per supervisor cycle
            message_timeout: Seconds to wait for a message before forcing reconnect
            on_error: Optional callback invoked on permanent failures
            supervisor_retries: Max supervisor restart cycles (0 = no supervisor)
            supervisor_cooldown: Seconds to wait between supervisor restarts
        """
        supervisor_attempts = 0

        while True:
            try:
                await self._listen_for_trades_inner(max_reconnects, message_timeout)
                # Inner loop exited cleanly (max_reconnects exhausted)
            except Exception as exc:
                logger.error("RTDS listen_for_trades inner loop error: %s", exc)

            # Check if supervisor should restart
            supervisor_attempts += 1
            if supervisor_attempts > supervisor_retries:
                logger.error(
                    "RTDS supervisor exhausted after %d retries, giving up",
                    supervisor_retries,
                )
                self.subscriptions.clear()
                self._ws_permanently_failed = True
                if on_error:
                    try:
                        on_error(Exception(
                            f"WebSocket permanently failed after {supervisor_retries} supervisor retries"
                        ))
                    except Exception:
                        pass
                return

            logger.error(
                "RTDS reconnects exhausted, supervisor restarting in %.0fs (attempt %d/%d)",
                supervisor_cooldown,
                supervisor_attempts,
                supervisor_retries,
            )
            if on_error:
                try:
                    on_error(Exception(
                        f"WebSocket reconnects exhausted, supervisor restart {supervisor_attempts}/{supervisor_retries}"
                    ))
                except Exception:
                    pass

            await asyncio.sleep(supervisor_cooldown)

            # Reset connection state for fresh start
            self.ws_connection = None

    async def _listen_for_trades_inner(self, max_reconnects: int, message_timeout: float):
        """Inner reconnect loop for RTDS trade listening."""
        reconnect_attempts = 0

        while reconnect_attempts <= max_reconnects:
            if not self.ws_connection:
                if reconnect_attempts > 0:
                    wait = min(2 ** reconnect_attempts, 30)
                    await asyncio.sleep(wait)
                    try:
                        await self.connect_websocket()
                        # Re-subscribe after reconnecting
                        if self.subscriptions:
                            subscribe_msg = {
                                "action": "subscribe",
                                "subscriptions": [{"topic": "activity", "type": "trades"}]
                            }
                            await self.ws_connection.send(json.dumps(subscribe_msg))
                    except Exception:
                        reconnect_attempts += 1
                        continue
                else:
                    raise Exception("WebSocket not connected")

            try:
                while True:
                    try:
                        message = await asyncio.wait_for(
                            self.ws_connection.recv(),
                            timeout=message_timeout,
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            "RTDS message timeout (%.0fs), forcing reconnect",
                            message_timeout,
                        )
                        # Force close stale connection
                        try:
                            await self.ws_connection.close()
                        except Exception:
                            pass
                        self.ws_connection = None
                        reconnect_attempts += 1
                        break

                    # Reset reconnect counter on successful message
                    reconnect_attempts = 0

                    try:
                        # Handle ping messages
                        if message == "PING":
                            await self.ws_connection.send("PONG")
                            continue

                        # Skip empty messages
                        if not message or message.strip() == "":
                            continue

                        data = json.loads(message)

                        # Only process messages with payload (actual trade data)
                        if "payload" not in data:
                            continue

                        # Handle RTDS trade messages
                        if data.get("topic") == "activity" and data.get("type") == "trades":
                            payload = data.get("payload", {})

                            event_slug = payload.get("eventSlug", "")
                            market_slug = payload.get("slug", "")

                            callback = None
                            if event_slug and event_slug in self.subscriptions:
                                callback = self.subscriptions[event_slug]
                            elif market_slug and market_slug in self.subscriptions:
                                callback = self.subscriptions[market_slug]
                            elif "_all" in self.subscriptions:
                                callback = self.subscriptions["_all"]

                            if callback:
                                result = callback(data)
                                # Support both sync and async callbacks
                                if hasattr(result, '__await__'):
                                    await result

                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue

            except websockets.exceptions.ConnectionClosed:
                self.ws_connection = None
                reconnect_attempts += 1
                if reconnect_attempts <= max_reconnects:
                    continue
                break
            except Exception:
                self.ws_connection = None
                reconnect_attempts += 1
                if reconnect_attempts <= max_reconnects:
                    continue
                break
    
    async def close_websocket(self):
        """Close any active WebSocket connections."""
        if self.ws_connection:
            try:
                await self.ws_connection.close()
            except Exception:
                pass
            finally:
                self.ws_connection = None

        if self.clob_ws:
            try:
                await self.clob_ws.close()
            except Exception:
                pass
            finally:
                self.clob_ws = None

        self.subscriptions.clear()
        if hasattr(self, '_ob_callback'):
            self._ob_callback = None
        if hasattr(self, '_ob_resolution_callback'):
            self._ob_resolution_callback = None
        if hasattr(self, '_ob_token_ids'):
            self._ob_token_ids = []
    
    def close(self):
        """Close REST session and best-effort close active websockets."""
        self.session.close()
        if not self.ws_connection and not self.clob_ws:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self.close_websocket())
        else:
            asyncio.run(self.close_websocket())

    # CLOB Order Book WebSocket Methods

    CLOB_WS_ENDPOINT = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    async def connect_clob_websocket(self):
        """Connect to CLOB order book WebSocket"""
        if not HAS_WEBSOCKETS:
            raise Exception("websockets library not installed. Install with: pip install websockets")

        try:
            self.clob_ws = await websockets.connect(self.CLOB_WS_ENDPOINT)
            return True
        except Exception as e:
            raise Exception(f"Failed to connect to CLOB WebSocket: {e}")

    async def subscribe_orderbook(self, token_ids, callback, resolution_callback=None):
        """Subscribe to real-time order book updates

        Message types: book, last_trade_price, price_change, tick_size_change,
        market_resolved (when custom_feature_enabled is set)
        Subscribe: {"assets_ids": [token_id1, ...], "type": "market", "custom_feature_enabled": true}

        Args:
            token_ids: List of CLOB token IDs to subscribe to
            callback: Function to call with order book update data
            resolution_callback: Optional callback for market_resolved events
        """
        if not hasattr(self, 'clob_ws') or not self.clob_ws:
            await self.connect_clob_websocket()

        subscribe_msg = {
            "assets_ids": token_ids,
            "type": "market",
            "custom_feature_enabled": True,
        }
        await self.clob_ws.send(json.dumps(subscribe_msg))
        self._ob_callback = callback
        self._ob_resolution_callback = resolution_callback
        self._ob_token_ids = token_ids

    async def listen_orderbook(self, max_reconnects=5, message_timeout: float = 60.0):
        """Listen for order book update messages from CLOB WebSocket

        Handles message types:
        - book: Full or partial order book update
        - last_trade_price: Latest trade price change
        - price_change: Market price movement

        Args:
            max_reconnects: Max reconnect attempts before giving up
            message_timeout: Seconds to wait for a message before forcing reconnect
        """
        reconnect_attempts = 0

        while reconnect_attempts <= max_reconnects:
            if not hasattr(self, 'clob_ws') or not self.clob_ws:
                if reconnect_attempts > 0:
                    wait = min(2 ** reconnect_attempts, 30)
                    await asyncio.sleep(wait)
                    try:
                        await self.connect_clob_websocket()
                        if hasattr(self, '_ob_token_ids') and self._ob_token_ids:
                            subscribe_msg = {
                                "assets_ids": self._ob_token_ids,
                                "type": "market",
                                "custom_feature_enabled": True,
                            }
                            await self.clob_ws.send(json.dumps(subscribe_msg))
                    except Exception:
                        reconnect_attempts += 1
                        continue
                else:
                    raise Exception("CLOB WebSocket not connected")

            try:
                while True:
                    try:
                        message = await asyncio.wait_for(
                            self.clob_ws.recv(),
                            timeout=message_timeout,
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Orderbook message timeout (%.0fs), forcing reconnect",
                            message_timeout,
                        )
                        try:
                            await self.clob_ws.close()
                        except Exception:
                            pass
                        self.clob_ws = None
                        reconnect_attempts += 1
                        break

                    reconnect_attempts = 0

                    try:
                        if not message or message.strip() == "":
                            continue

                        data = json.loads(message)

                        # Handle different message types
                        msg_type = data.get("type", data.get("event_type", ""))
                        if msg_type == "market_resolved":
                            if hasattr(self, '_ob_resolution_callback') and self._ob_resolution_callback:
                                result = self._ob_resolution_callback(data)
                                if hasattr(result, '__await__'):
                                    await result
                        elif msg_type in ("book", "last_trade_price", "price_change", "tick_size_change"):
                            if hasattr(self, '_ob_callback') and self._ob_callback:
                                result = self._ob_callback(data)
                                if hasattr(result, '__await__'):
                                    await result
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue

            except Exception:
                if hasattr(self, 'clob_ws'):
                    self.clob_ws = None
                reconnect_attempts += 1
                if reconnect_attempts <= max_reconnects:
                    continue
                break

        if hasattr(self, '_ob_callback'):
            self._ob_callback = None
        if hasattr(self, '_ob_resolution_callback'):
            self._ob_resolution_callback = None

    # Utility Methods

    def calculate_spread(self, order_book: Dict[str, Any]) -> float:
        """Calculate bid-ask spread from order book

        Args:
            order_book: Order book dictionary

        Returns:
            Spread as percentage
        """
        if not order_book.get("bids") or not order_book.get("asks"):
            return 0.0

        # Handle both formats: list of dicts with 'price' key, or list of [price, size]
        first_bid = order_book["bids"][0]
        first_ask = order_book["asks"][0]

        if isinstance(first_bid, dict):
            best_bid = float(first_bid.get("price", 0))
            best_ask = float(first_ask.get("price", 0))
        else:
            best_bid = float(first_bid[0])
            best_ask = float(first_ask[0])

        if best_bid == 0:
            return 0.0

        spread = ((best_ask - best_bid) / best_bid) * 100
        return spread
    
    def get_current_markets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get current active markets from the paginated sampling endpoint.
        
        Args:
            limit: Maximum number of markets
        
        Returns:
            List of current market dictionaries
        """
        try:
            url = f"{self.rest_endpoint}/sampling-markets"
            markets: List[Dict[str, Any]] = []
            next_cursor = None

            while len(markets) < limit:
                page_limit = min(max(limit - len(markets), 1), 1000)
                params = {"limit": page_limit}
                if next_cursor:
                    params["next_cursor"] = next_cursor

                response = self._request("GET", url, params=params)
                response.raise_for_status()
                data = response.json()
                page = data.get('data', []) if isinstance(data, dict) else []
                if not isinstance(page, list):
                    page = []

                markets.extend(page)
                next_cursor = data.get("next_cursor") if isinstance(data, dict) else None
                if not next_cursor or next_cursor == "LTE=" or len(page) < page_limit:
                    break

            return markets[:limit]
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get current markets: {e}")
    
    def is_market_current(self, market: Dict[str, Any]) -> bool:
        """Check if market is current (2025 or later, not closed)
        
        Args:
            market: Market dictionary
        
        Returns:
            True if market is current
        """
        try:
            # Check if closed
            if market.get('closed', False):
                return False
            
            # Check end date
            end_date_str = market.get('end_date_iso', market.get('end_date', ''))
            if not end_date_str:
                return market.get('active', False)  # If no date, rely on active flag
            
            # Parse date
            if HAS_DATEUTIL:
                end_date = parser.parse(end_date_str)
            else:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            
            # Must be from current year or future
            if end_date.year < datetime.now().year:
                return False
            
            # Must not be in the past
            if end_date < datetime.now(end_date.tzinfo) if end_date.tzinfo else datetime.now():
                return False
                
            return True
        except Exception:
            return False
    
    def detect_large_trade(self, trade: Dict[str, Any], threshold: float = 10000) -> bool:
        """Detect if a trade is "large" (whale trade)
        
        Args:
            trade: Trade dictionary
            threshold: Minimum notional value for large trade
        
        Returns:
            True if trade is large
        """
        size = float(trade.get("size", 0))
        price = float(trade.get("price", 0))
        notional = size * price
        
        return notional >= threshold
