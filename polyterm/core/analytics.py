"""Analytics engine for whale tracking, correlations, and predictions"""

import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..api.gamma import GammaClient
from ..api.clob import CLOBClient
from ..api.subgraph import SubgraphClient


class WhaleActivity:
    """Represents a whale trade or activity"""
    
    def __init__(self, trade_data: Dict[str, Any]):
        self.data = trade_data  # Store original data
        self.trader = trade_data.get("trader", "")
        self.market_id = trade_data.get("market", "")
        self.outcome = trade_data.get("outcome", "")
        self.shares = float(trade_data.get("shares", 0))
        self.price = float(trade_data.get("price", 0))
        self.notional = float(trade_data.get("notional", self.shares * self.price))
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
        subgraph_client: SubgraphClient,
    ):
        self.gamma_client = gamma_client
        self.clob_client = clob_client
        self.subgraph_client = subgraph_client
        
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
                    # Get nested market data for price info
                    nested_markets = market.get('markets', [])
                    last_price = 0
                    outcome = "Unknown"
                    
                    if nested_markets:
                        nested = nested_markets[0]
                        last_price = float(nested.get('lastTradePrice', 0) or 0)
                        prices = nested.get('outcomePrices', [])
                        
                        # Handle outcomePrices which might be a JSON string
                        if isinstance(prices, str):
                            import json
                            try:
                                prices = json.loads(prices)
                            except:
                                prices = []
                        
                        if prices and len(prices) > 0:
                            try:
                                outcome = "YES" if float(prices[0]) > 0.5 else "NO"
                            except:
                                outcome = "Unknown"
                    
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
        try:
            # Get historical data for both markets
            # This is a simplified version - real implementation would need time series data
            
            market1_trades = self.subgraph_client.get_market_trades(
                market1_id,
                first=100,
            )
            market2_trades = self.subgraph_client.get_market_trades(
                market2_id,
                first=100,
            )
            
            if not market1_trades or not market2_trades:
                return None
            
            # Calculate simple correlation based on price movements
            # This is a placeholder - real implementation would use proper time series correlation
            
            correlation = 0.0  # Placeholder
            
            return MarketCorrelation(market1_id, market2_id, correlation)
            
        except Exception as e:
            print(f"Error calculating correlation: {e}")
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
        try:
            # Get market statistics
            stats = self.subgraph_client.get_market_statistics(market_id)
            
            # Get trades in time window
            end_time = int(time.time())
            start_time = end_time - (hours * 3600)
            
            volume_data = self.subgraph_client.get_market_volume(
                market_id,
                start_time=start_time,
                end_time=end_time,
            )
            
            trades = self.subgraph_client.get_market_trades(
                market_id,
                first=1000,
            )
            
            # Filter trades in time window
            recent_trades = [
                t for t in trades
                if start_time <= int(t.get("timestamp", 0)) <= end_time
            ]
            
            # Calculate trend metrics
            total_volume = sum(float(t.get("shares", 0)) * float(t.get("price", 0)) for t in recent_trades)
            avg_trade_size = total_volume / len(recent_trades) if recent_trades else 0
            
            # Price trend
            if len(recent_trades) >= 2:
                first_price = float(recent_trades[-1].get("price", 0))
                last_price = float(recent_trades[0].get("price", 0))
                price_change = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0
            else:
                price_change = 0
            
            return {
                "market_id": market_id,
                "time_window_hours": hours,
                "total_trades": len(recent_trades),
                "total_volume": total_volume,
                "average_trade_size": avg_trade_size,
                "price_change_percent": price_change,
                "trend_direction": "up" if price_change > 0 else "down" if price_change < 0 else "flat",
            }
            
        except Exception as e:
            print(f"Error analyzing trends: {e}")
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
        """Get analytics for a user's portfolio (limited without Subgraph)
        
        Args:
            wallet_address: User wallet address
        
        Returns:
            Portfolio analytics with available data
        """
        try:
            # Try Subgraph first (may not work if endpoint removed)
            positions = self.subgraph_client.get_user_positions(wallet_address)
            
            total_value = 0
            total_pnl = 0
            position_count = len(positions)
            
            for position in positions:
                shares = float(position.get("shares", 0))
                avg_price = float(position.get("averagePrice", 0))
                realized_pnl = float(position.get("realizedPnL", 0))
                unrealized_pnl = float(position.get("unrealizedPnL", 0))
                
                position_value = shares * avg_price
                total_value += position_value
                total_pnl += realized_pnl + unrealized_pnl
            
            return {
                "wallet_address": wallet_address,
                "total_positions": position_count,
                "total_value": total_value,
                "total_pnl": total_pnl,
                "roi_percent": (total_pnl / total_value * 100) if total_value > 0 else 0,
                "positions": positions,
            }
            
        except Exception as e:
            # Graceful degradation - return empty portfolio with error message
            return {
                "wallet_address": wallet_address,
                "total_positions": 0,
                "total_value": 0,
                "total_pnl": 0,
                "roi_percent": 0,
                "positions": [],
                "error": "Portfolio data unavailable - Subgraph API endpoint has been removed",
                "note": "Historical position tracking requires on-chain data access",
            }
    
    def detect_market_manipulation(self, market_id: str) -> Dict[str, Any]:
        """Detect potential market manipulation patterns
        
        Args:
            market_id: Market ID
        
        Returns:
            Manipulation risk analysis
        """
        try:
            # Get liquidity changes
            liquidity_events = self.subgraph_client.get_market_liquidity_changes(
                market_id,
                first=50,
            )
            
            # Get recent trades
            trades = self.subgraph_client.get_market_trades(market_id, first=100)
            
            # Check for suspicious patterns
            risk_factors = []
            risk_score = 0
            
            # 1. Sudden liquidity withdrawal
            if liquidity_events:
                withdrawals = [e for e in liquidity_events if e.get("type") == "remove"]
                if len(withdrawals) > 3:
                    risk_factors.append("Multiple liquidity withdrawals")
                    risk_score += 20
            
            # 2. Wash trading (same trader buying and selling)
            trader_activity = defaultdict(list)
            for trade in trades[:20]:  # Recent trades
                trader = trade.get("trader")
                trader_activity[trader].append(trade)
            
            for trader, trader_trades in trader_activity.items():
                if len(trader_trades) >= 4:
                    risk_factors.append(f"High frequency trading by {trader[:8]}...")
                    risk_score += 15
            
            # 3. Price manipulation (rapid swings)
            if len(trades) >= 10:
                prices = [float(t.get("price", 0)) for t in trades[:10]]
                price_range = max(prices) - min(prices)
                if price_range > 0.3:  # 30% swing
                    risk_factors.append("Rapid price swings")
                    risk_score += 25
            
            risk_level = "high" if risk_score >= 50 else "medium" if risk_score >= 25 else "low"
            
            return {
                "market_id": market_id,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
            }
            
        except Exception as e:
            print(f"Error detecting manipulation: {e}")
            return {"risk_level": "unknown", "error": str(e)}

