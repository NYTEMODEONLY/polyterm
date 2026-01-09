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
    
    # REST API Methods
    
    def get_order_book(self, market_id: str, depth: int = 20) -> Dict[str, Any]:
        """Get order book for a market
        
        Args:
            market_id: Market ID
            depth: Order book depth (number of price levels)
        
        Returns:
            Order book with bids and asks
        """
        url = f"{self.rest_endpoint}/book/{market_id}"
        params = {"depth": depth}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
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
            market_slugs: List of market slugs to monitor
            callback: Function to call when trade data is received
        """
        if not self.ws_connection:
            await self.connect_websocket()
        
        # Subscribe to RTDS trades topic with correct format
        # RTDS requires individual subscriptions for each market
        for market_slug in market_slugs:
            subscribe_msg = {
                "action": "subscribe",
                "subscriptions": [
                    {
                        "topic": "activity",
                        "type": "trades",
                        "filters": f"{{\"market_slug\":\"{market_slug}\"}}"
                    }
                ]
            }
            await self.ws_connection.send(json.dumps(subscribe_msg))
        
        # Store callback for all markets
        for market_slug in market_slugs:
            self.subscriptions[market_slug] = callback
    
    async def listen_for_trades(self):
        """Listen for incoming trade messages from RTDS"""
        if not self.ws_connection:
            raise Exception("WebSocket not connected")
        
        try:
            async for message in self.ws_connection:
                try:
                    # Handle ping messages
                    if message == "PING":
                        await self.ws_connection.send("PONG")
                        continue
                    
                    data = json.loads(message)
                    
                    # Handle RTDS trade messages with correct topic/type
                    if data.get("topic") == "activity" and data.get("type") == "trades":
                        # Extract market identifier from the trade data
                        # The official client shows 'market' field contains the market identifier
                        market_id = data.get("market") or data.get("market_slug")
                        if market_id and market_id in self.subscriptions:
                            callback = self.subscriptions[market_id]
                            await callback(data)
                    
                    # Handle other activity messages
                    elif data.get("topic") == "activity":
                        market_id = data.get("market") or data.get("market_slug")
                        if market_id and market_id in self.subscriptions:
                            callback = self.subscriptions[market_id]
                            await callback(data)
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error processing message: {e}")
                    continue
                    
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"WebSocket error: {e}")
    
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
        
        best_bid = float(order_book["bids"][0][0])
        best_ask = float(order_book["asks"][0][0])
        
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

