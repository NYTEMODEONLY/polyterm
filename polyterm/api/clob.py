"""CLOB (Central Limit Order Book) API client"""

import asyncio
import json
import requests
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

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
        self.subscriptions = {}

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
                        wait = min(int(retry_after), 60)
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

        return response

    # REST API Methods

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
    
    def get_ticker(self, market_id: str) -> Dict[str, Any]:
        """Get ticker data for a market
        
        Args:
            market_id: Market ID
        
        Returns:
            Ticker with last price, volume, etc.
        """
        url = f"{self.rest_endpoint}/ticker/{market_id}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get ticker: {e}")
    
    def get_recent_trades(self, market_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades for a market
        
        Args:
            market_id: Market ID
            limit: Maximum number of trades
        
        Returns:
            List of recent trades
        """
        url = f"{self.rest_endpoint}/trades/{market_id}"
        params = {"limit": limit}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get trades: {e}")
    
    def get_market_depth(self, market_id: str) -> Dict[str, Any]:
        """Get market depth statistics
        
        Args:
            market_id: Market ID
        
        Returns:
            Market depth statistics
        """
        url = f"{self.rest_endpoint}/depth/{market_id}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get market depth: {e}")
    
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
    
    async def listen_for_trades(self, max_reconnects: int = 5):
        """Listen for incoming trade messages from RTDS with auto-reconnection"""
        reconnect_attempts = 0

        while reconnect_attempts <= max_reconnects:
            if not self.ws_connection:
                if reconnect_attempts > 0:
                    # Exponential backoff for reconnection
                    import asyncio as _asyncio
                    wait = min(2 ** reconnect_attempts, 30)
                    _asyncio.get_event_loop()  # verify loop exists
                    await _asyncio.sleep(wait)
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
                async for message in self.ws_connection:
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

        # Clear subscriptions on permanent failure
        self.subscriptions.clear()
    
    async def close_websocket(self):
        """Close WebSocket connection"""
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None
    
    def close(self):
        """Close REST session"""
        self.session.close()
    
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
        """Get current active markets (uses sampling-markets endpoint)
        
        Args:
            limit: Maximum number of markets
        
        Returns:
            List of current market dictionaries
        """
        url = f"{self.rest_endpoint}/sampling-markets"
        params = {"limit": limit}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
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

