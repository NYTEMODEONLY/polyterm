"""Analytics engine for whale tracking, correlations, and predictions"""

from typing import Dict, List, Optional, Any, NoReturn
from collections import defaultdict

from ..api.gamma import GammaClient
from ..api.clob import CLOBClient
from ..api.data_api import DataAPIClient
from ..api.data_api_lag import label_payload
from ..utils.json_output import safe_float
from ..utils.errors import FeatureUnavailable
from .volume_spikes import EVIDENCE_LEVEL as VOLUME_SPIKE_EVIDENCE, detect_high_volume_markets


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
        self.evidence_level = trade_data.get("evidence_level", "")
    
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
        """Return high-volume market heuristics, not attributable whale trades.

        Prefer ``volume_spikes.detect_high_volume_markets`` or
        ``WalletIntelligence.live_whales`` for wallet-level public trades.
        ``lookback_hours`` is accepted for call-site compatibility; Gamma
        ``volume24hr`` is a 24h market aggregate, not a trade window.
        """
        try:
            markets = detect_high_volume_markets(
                self.gamma_client,
                min_volume=min_notional,
            )
            activities = []
            for market in markets:
                last_price = market.last_price if market.last_price > 0 else 1
                activities.append(
                    WhaleActivity({
                        "trader": "",
                        "market": market.market_id,
                        "outcome": market.outcome_lean,
                        "shares": market.volume_24hr / last_price,
                        "price": market.last_price,
                        "notional": market.volume_24hr,
                        "timestamp": market.timestamp,
                        "transactionHash": "",
                        "evidence_level": VOLUME_SPIKE_EVIDENCE,
                        "_market_title": market.market_title,
                    })
                )
            _ = lookback_hours
            return activities
        except Exception as e:
            print(f"Error tracking high-volume markets: {e}")
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
    
    def _unavailable(self, feature: str) -> NoReturn:
        raise FeatureUnavailable(
            f"{feature} is not implemented and has no data source.",
            suggestion=(
                "Use CorrelationEngine with real CLOB price history, "
                "or polyterm chart / polyterm replay."
            ),
            details=feature,
        )

    def identify_whale_followers(self, whale_address: str) -> List[Dict[str, Any]]:
        """Identify traders who follow whale activity.

        Not implemented. Raises instead of returning [].
        """
        self._unavailable("identify_whale_followers")
    
    def calculate_market_correlation(
        self,
        market1_id: str,
        market2_id: str,
        window_hours: int = 24,
    ) -> Optional[MarketCorrelation]:
        """Calculate correlation between two markets.

        Not implemented. Raises instead of returning None.
        """
        self._unavailable("calculate_market_correlation")
    
    def find_correlated_markets(
        self,
        market_id: str,
        min_correlation: float = 0.7,
        limit: int = 5,
    ) -> List[MarketCorrelation]:
        """Find markets correlated with given market.

        Not implemented. Raises instead of returning [].
        """
        self._unavailable("find_correlated_markets")
    
    def analyze_historical_trends(
        self,
        market_id: str,
        hours: int = 168,  # 1 week
    ) -> Dict[str, Any]:
        """Analyze historical trends for a market.

        Not implemented. Raises instead of returning {}.
        """
        self._unavailable("analyze_historical_trends")
    
    def predict_price_movement(
        self,
        market_id: str,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """Predict price movement using trend plus volume signals.

        Not implemented: it depended on analyze_historical_trends,
        which has no data source. Raises instead of inventing a signal.
        """
        self._unavailable("predict_price_movement")
    
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

            # Primary source: lagged Data API wallet positions (not live CLOB)
            positions = data_api_client.get_positions(wallet_address, limit=500, sort_by="CURRENT")
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
            
            return label_payload({
                "wallet_address": wallet_address,
                "total_positions": position_count,
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_invested": total_invested,
                "roi_percent": (total_pnl / total_invested * 100) if total_invested > 0 else 0,
                "positions": positions,
                "data_source": "data_api",
            })
            
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
        """Detect potential market manipulation patterns.

        Not implemented. Raises instead of returning a fake risk_score of 0.
        """
        self._unavailable("detect_market_manipulation")
