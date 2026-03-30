"""Analytics engine for whale tracking, correlations, and predictions"""

import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..api.gamma import GammaClient
from ..api.clob import CLOBClient
from ..api.data_api import DataAPIClient
from ..utils.json_output import safe_float


class WhaleActivity:
    """Represents a whale trade or activity"""
    
    def __init__(self, trade_data: Dict[str, Any]):
        self.data = trade_data  # Store original data
        self.trader = trade_data.get("trader", "")
        self.market_id = trade_data.get("market", "")
        self.outcome = trade_data.get("outcome", "")
        self.shares = safe_float(trade_data.get("shares", 0))
        self.price = safe_float(trade_data.get("price", 0))
        self.notional = safe_float(trade_data.get("notional", self.shares * self.price))
        self.timestamp = int(trade_data.get("timestamp", 0))
        self.tx_hash = trade_data.get("transactionHash", "")
    
    def __repr__(self):
        return f"WhaleActivity(trader={self.trader[:8]}..., notional=${self.notional:,.0f})"


class MarketCorrelation:
    """Represents correlation between two markets"""
    
    def __init__(self, market1_id: str, market2_id: str, correlation: float):
        self.market1_id = market1_id
        self.market2_id = market2_id
        self.correlation = correlation
    
    def __repr__(self):
        return f"Correlation({self.market1_id} <-> {self.market2_id}): {self.correlation:.3f}"


class AnalyticsEngine:
    """Advanced analytics for market monitoring"""
    
    def __init__(
        self,
        gamma_client: GammaClient,
        clob_client: CLOBClient,
        data_api_client: Optional[DataAPIClient] = None,
    ):
        self.gamma_client = gamma_client
        self.clob_client = clob_client
        self.data_api_client = data_api_client
        
        # Cache for whale traders
        self.known_whales: Dict[str, List[WhaleActivity]] = defaultdict(list)
        
        # Cache for market data
        self.market_cache: Dict[str, Dict[str, Any]] = {}
    
    def track_whale_trades(
        self,
        min_notional: float = 10000,
        lookback_hours: int = 24,
    ) -> List[WhaleActivity]:
        """Track whale activity using volume spikes (individual trades not available from API)
        
        Args:
            min_notional: Minimum volume spike to be considered whale activity
            lookback_hours: Hours to look back
        
        Returns:
            List of whale activities (volume-based detection)
        """
        try:
            # Get active markets from Gamma
            markets = self.gamma_client.get_markets(limit=50, active=True, closed=False)
            
            activities = []
            current_time = int(time.time())
            
            for market in markets:
                market_id = market.get('id')
                if not market_id:
                    continue
                
                # Check for volume spikes as proxy for whale activity
                volume_24hr = float(market.get('volume24hr', 0) or 0)
                
                # If significant volume in last 24hrs, could indicate whale activity
                if volume_24hr >= min_notional:
                    # Get price info - check direct fields first (from /markets endpoint)
                    # then fall back to nested markets (from /events endpoint)
                    last_price = float(market.get('lastTradePrice', 0) or 0)
                    prices = market.get('outcomePrices', [])
                    outcome = "Unknown"

                    # Handle outcomePrices which might be a JSON string
                    if isinstance(prices, str):
                        import json
                        try:
                            prices = json.loads(prices)
                        except Exception:
                            prices = []

                    # Determine trend based on YES price (first outcome)
                    if prices and len(prices) > 0:
                        try:
                            yes_price = float(prices[0])
                            # Use price thresholds to determine market direction
                            if yes_price > 0.65:
                                outcome = "YES"  # Leaning YES
                            elif yes_price < 0.35:
                                outcome = "NO"   # Leaning NO
                            else:
                                outcome = "MIXED"  # Uncertain/competitive
                            # Also use this as last_price if not already set
                            if last_price == 0:
                                last_price = yes_price
                        except Exception:
                            pass

                    # Fall back to nested markets if no direct price data
                    if last_price == 0 or outcome == "Unknown":
                        nested_markets = market.get('markets', [])
                        if nested_markets:
                            nested = nested_markets[0]
                            if last_price == 0:
                                last_price = float(nested.get('lastTradePrice', 0) or 0)
                            nested_prices = nested.get('outcomePrices', [])
                            if isinstance(nested_prices, str):
                                import json
                                try:
                                    nested_prices = json.loads(nested_prices)
                                except Exception:
                                    nested_prices = []
                            if nested_prices and len(nested_prices) > 0 and outcome == "Unknown":
                                try:
                                    yes_price = float(nested_prices[0])
                                    if yes_price > 0.65:
                                        outcome = "YES"
                                    elif yes_price < 0.35:
                                        outcome = "NO"
                                    else:
                                        outcome = "MIXED"
                                except Exception:
                                    pass
                    
                    # Store market title for display
                    market_title = market.get('title', market.get('question', 'Unknown'))
                    
                    # Create activity based on volume spike
                    activity = WhaleActivity({
                        'trader': 'Volume Spike',  # Can't determine individual trader
                        'market': market_id,
                        'outcome': outcome,
                        'shares': volume_24hr / (last_price if last_price > 0 else 1),
                        'price': last_price,
                        'notional': volume_24hr,
                        'timestamp': current_time,
                        'transactionHash': '',
                        '_market_title': market_title,  # Cache title
                    })
                    activities.append(activity)
            
            return sorted(activities, key=lambda x: x.notional, reverse=True)
            
        except Exception as e:
            print(f"Error tracking whale trades: {e}")
            return []
    
    def get_whale_impact_on_market(
        self,
        market_id: str,
        whale_address: str,
    ) -> Dict[str, Any]:
        """Analyze a whale's impact on a specific market
        
        Args:
            market_id: Market ID
            whale_address: Whale wallet address
        
        Returns:
            Impact statistics
        """
        if whale_address not in self.known_whales:
            return {"total_trades": 0, "total_volume": 0, "net_position": 0}
        
        trades = [
            t for t in self.known_whales[whale_address]
            if t.market_id == market_id
        ]
        
        total_volume = sum(t.notional for t in trades)
        buy_volume = sum(t.notional for t in trades if t.outcome == "YES")
        sell_volume = sum(t.notional for t in trades if t.outcome == "NO")
        
        return {
            "total_trades": len(trades),
            "total_volume": total_volume,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "net_position": buy_volume - sell_volume,
            "trades": trades,
        }
    
    def identify_whale_followers(self, whale_address: str) -> List[Dict[str, Any]]:
        """Identify traders who follow whale activity
        
        Args:
            whale_address: Whale wallet address
        
        Returns:
            List of potential follower addresses with statistics
        """
        # This would require more sophisticated analysis
        # For now, return a placeholder
        return []
    
    def calculate_market_correlation(
        self,
        market1_id: str,
        market2_id: str,
        window_hours: int = 24,
    ) -> Optional[MarketCorrelation]:
        """Calculate correlation between two markets

        Args:
            market1_id: First market ID
            market2_id: Second market ID
            window_hours: Time window for correlation

        Returns:
            Correlation object or None
        """
        # Placeholder — requires time-series data source
        return None
    
    def find_correlated_markets(
        self,
        market_id: str,
        min_correlation: float = 0.7,
        limit: int = 5,
    ) -> List[MarketCorrelation]:
        """Find markets correlated with given market
        
        Args:
            market_id: Market to find correlations for
            min_correlation: Minimum correlation threshold
            limit: Maximum number of results
        
        Returns:
            List of correlated markets
        """
        # Placeholder - would need to calculate against all markets
        return []
    
    def analyze_historical_trends(
        self,
        market_id: str,
        hours: int = 168,  # 1 week
    ) -> Dict[str, Any]:
        """Analyze historical trends for a market

        Args:
            market_id: Market ID
            hours: Hours of history to analyze

        Returns:
            Trend statistics
        """
        # Historical trend analysis requires a time-series data source.
        # The Subgraph endpoint has been removed; return empty until a
        # replacement (e.g. CLOB price history) is wired in.
        return {}
    
    def predict_price_movement(
        self,
        market_id: str,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """Predict price movement using basic signals
        
        Args:
            market_id: Market ID
            horizon_hours: Prediction horizon
        
        Returns:
            Prediction with confidence
        """
        try:
            # Get recent trends
            trends = self.analyze_historical_trends(market_id, hours=168)
            
            # Get current whale activity
            whale_trades = self.track_whale_trades(lookback_hours=24)
            market_whale_activity = [w for w in whale_trades if w.market_id == market_id]
            
            # Simple prediction based on momentum and whale activity
            price_momentum = trends.get("price_change_percent", 0)
            whale_net_position = sum(
                w.notional if w.outcome == "YES" else -w.notional
                for w in market_whale_activity
            )
            
            # Combined signal
            signal = (price_momentum * 0.6) + (whale_net_position / 10000 * 0.4)
            
            if signal > 5:
                prediction = "up"
                confidence = min(abs(signal) / 20, 1.0)
            elif signal < -5:
                prediction = "down"
                confidence = min(abs(signal) / 20, 1.0)
            else:
                prediction = "stable"
                confidence = 0.5
            
            return {
                "market_id": market_id,
                "prediction": prediction,
                "confidence": confidence,
                "signal_strength": signal,
                "factors": {
                    "price_momentum": price_momentum,
                    "whale_activity": whale_net_position,
                },
            }
            
        except Exception as e:
            print(f"Error predicting price movement: {e}")
            return {
                "prediction": "unknown",
                "confidence": 0.0,
                "error": str(e),
            }
    
    def get_portfolio_analytics(self, wallet_address: str) -> Dict[str, Any]:
        """Get analytics for a user's portfolio.
        
        Args:
            wallet_address: User wallet address
        
        Returns:
            Portfolio analytics with available data
        """
        try:
            data_api_client = self.data_api_client
            if data_api_client is None:
                data_api_client = DataAPIClient()

            if data_api_client is None:
                raise RuntimeError("Data API client not configured")

            # Primary source: Data API (live wallet positions/trades)
            positions = data_api_client.get_positions(wallet_address, limit=500, sort_by="CURRENT_VALUE")
            if not isinstance(positions, list):
                positions = []

            total_value = 0
            total_pnl = 0
            total_invested = 0
            position_count = len(positions)
            
            for position in positions:
                shares = safe_float(
                    position.get("size", position.get("shares", position.get("quantity", 0)))
                )
                avg_price = safe_float(
                    position.get("averagePrice", position.get("avgPrice", position.get("entryPrice", 0)))
                )
                current_value_raw = position.get("currentValue")
                if current_value_raw is None:
                    current_value_raw = position.get("value")
                if current_value_raw is None:
                    current_value_raw = position.get("current_value")
                has_current_value = current_value_raw not in (None, "")
                current_value = safe_float(current_value_raw)

                initial_value_raw = position.get("initialValue")
                if initial_value_raw is None:
                    initial_value_raw = position.get("costBasis")
                if initial_value_raw is None:
                    initial_value_raw = position.get("initial_value")
                has_initial_value = initial_value_raw not in (None, "")
                initial_value = safe_float(initial_value_raw)
                realized_pnl = safe_float(
                    position.get("realizedPnL", position.get("realizedPnl", 0))
                )
                unrealized_pnl = safe_float(
                    position.get("unrealizedPnL", position.get("unrealizedPnl", 0))
                )
                explicit_pnl = position.get("pnl")

                if (not has_current_value) and shares > 0 and avg_price > 0:
                    current_value = shares * avg_price
                if (not has_initial_value) and shares > 0 and avg_price > 0:
                    initial_value = shares * avg_price

                if explicit_pnl is not None:
                    position_pnl = safe_float(explicit_pnl)
                else:
                    position_pnl = realized_pnl + unrealized_pnl

                total_value += current_value
                total_pnl += position_pnl
                total_invested += initial_value
            
            return {
                "wallet_address": wallet_address,
                "total_positions": position_count,
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_invested": total_invested,
                "roi_percent": (total_pnl / total_invested * 100) if total_invested > 0 else 0,
                "positions": positions,
                "data_source": "data_api",
            }
            
        except Exception as e:
            # Graceful degradation when no position source is available
            return {
                "wallet_address": wallet_address,
                "total_positions": 0,
                "total_value": 0,
                "total_pnl": 0,
                "roi_percent": 0,
                "positions": [],
                "error": "Portfolio data unavailable from Data API",
                "note": str(e),
            }
    
    def detect_market_manipulation(self, market_id: str) -> Dict[str, Any]:
        """Detect potential market manipulation patterns

        Args:
            market_id: Market ID

        Returns:
            Manipulation risk analysis
        """
        # Manipulation detection required on-chain Subgraph data which is no
        # longer available.  Return a safe default until a replacement source
        # (e.g. CLOB trade history) is wired in.
        return {
            "market_id": market_id,
            "risk_level": "unknown",
            "risk_score": 0,
            "risk_factors": [],
        }
