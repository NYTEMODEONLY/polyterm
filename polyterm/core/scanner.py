"""Market scanner for detecting shifts and anomalies"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from ..api.gamma import GammaClient
from ..api.clob import CLOBClient
from ..api.subgraph import SubgraphClient
from ..api.aggregator import APIAggregator


class MarketSnapshot:
    """Snapshot of market data at a point in time"""
    
    def __init__(self, market_id: str, data: Dict[str, Any], timestamp: float):
        self.market_id = market_id
        self.data = data
        self.timestamp = timestamp
        
        # Extract key metrics
        self.probability = data.get("probability", 0.0)
        self.volume = data.get("volume", 0.0)
        self.liquidity = data.get("liquidity", 0.0)
        self.price = data.get("price", 0.0)
        self.title = data.get("title", data.get("question", ""))
        
        # Data source tracking
        self.data_sources = data.get("_data_sources", ["unknown"])
        self.is_fresh = data.get("_is_fresh", True)
        self.market_end_date = data.get("endDate", data.get("end_date_iso", ""))
    
    def calculate_shift(self, previous: "MarketSnapshot") -> Dict[str, float]:
        """Calculate changes from previous snapshot"""
        if not previous:
            return {
                "probability_change": 0.0,
                "volume_change": 0.0,
                "liquidity_change": 0.0,
                "price_change": 0.0,
            }
        
        prob_change = self.probability - previous.probability
        vol_change = ((self.volume - previous.volume) / previous.volume * 100) if previous.volume > 0 else 0
        liq_change = ((self.liquidity - previous.liquidity) / previous.liquidity * 100) if previous.liquidity > 0 else 0
        price_change = ((self.price - previous.price) / previous.price * 100) if previous.price > 0 else 0
        
        return {
            "probability_change": prob_change,
            "volume_change": vol_change,
            "liquidity_change": liq_change,
            "price_change": price_change,
        }


class MarketScanner:
    """Scanner for monitoring market shifts across multiple data sources"""
    
    def __init__(
        self,
        gamma_client: GammaClient,
        clob_client: CLOBClient,
        subgraph_client: SubgraphClient,
        check_interval: int = 60,
    ):
        self.gamma_client = gamma_client
        self.clob_client = clob_client
        self.subgraph_client = subgraph_client
        self.check_interval = check_interval
        
        # Initialize aggregator for live data with fallback
        self.aggregator = APIAggregator(gamma_client, clob_client, subgraph_client)
        
        # Storage for market snapshots
        self.snapshots: Dict[str, List[MarketSnapshot]] = {}
        self.max_snapshots_per_market = 100
        
        # Callbacks
        self.shift_callbacks: List[Callable] = []
        
        # State
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Data validation settings
        self.require_fresh_data = True
        self.max_data_age_hours = 24
    
    def add_shift_callback(self, callback: Callable):
        """Add callback to be called when shift is detected"""
        self.shift_callbacks.append(callback)
    
    def get_market_snapshot(self, market_id: str) -> Optional[MarketSnapshot]:
        """Get aggregated market snapshot from all sources"""
        try:
            # Fetch from multiple sources
            gamma_data = self.gamma_client.get_market(market_id)
            gamma_prices = self.gamma_client.get_market_prices(market_id)
            
            # Get CLOB data
            try:
                clob_ticker = self.clob_client.get_ticker(market_id)
                clob_book = self.clob_client.get_order_book(market_id)
            except:
                clob_ticker = {}
                clob_book = {}
            
            # Get on-chain data
            try:
                subgraph_stats = self.subgraph_client.get_market_statistics(market_id)
            except:
                subgraph_stats = {}
            
            # Aggregate data
            aggregated_data = {
                "market_id": market_id,
                "title": gamma_data.get("question", ""),
                "probability": float(gamma_prices.get("price", 0)) * 100,
                "price": float(gamma_prices.get("price", 0)),
                "volume": float(gamma_data.get("volume", 0)),
                "liquidity": float(gamma_data.get("liquidity", 0)),
                "last_trade_price": float(clob_ticker.get("last", 0)) if clob_ticker else 0,
                "spread": self.clob_client.calculate_spread(clob_book) if clob_book else 0,
                "on_chain_volume": float(subgraph_stats.get("totalVolume", 0)),
                "trade_count": int(subgraph_stats.get("tradeCount", 0)),
            }
            
            return MarketSnapshot(market_id, aggregated_data, time.time())
            
        except Exception as e:
            print(f"Error getting snapshot for {market_id}: {e}")
            return None
    
    def store_snapshot(self, snapshot: MarketSnapshot):
        """Store market snapshot with history limit"""
        if snapshot.market_id not in self.snapshots:
            self.snapshots[snapshot.market_id] = []
        
        self.snapshots[snapshot.market_id].append(snapshot)
        
        # Limit history
        if len(self.snapshots[snapshot.market_id]) > self.max_snapshots_per_market:
            self.snapshots[snapshot.market_id] = self.snapshots[snapshot.market_id][-self.max_snapshots_per_market:]
    
    def get_previous_snapshot(self, market_id: str) -> Optional[MarketSnapshot]:
        """Get previous snapshot for comparison"""
        if market_id not in self.snapshots or len(self.snapshots[market_id]) < 2:
            return None
        return self.snapshots[market_id][-2]
    
    def detect_shift(
        self,
        current: MarketSnapshot,
        previous: Optional[MarketSnapshot],
        thresholds: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """Detect if a significant shift occurred"""
        if not previous:
            return None
        
        changes = current.calculate_shift(previous)
        
        # Check thresholds
        shift_detected = False
        shift_type = []
        
        if abs(changes["probability_change"]) >= thresholds.get("probability", 10.0):
            shift_detected = True
            shift_type.append("probability")
        
        if abs(changes["volume_change"]) >= thresholds.get("volume", 50.0):
            shift_detected = True
            shift_type.append("volume")
        
        if abs(changes["liquidity_change"]) >= thresholds.get("liquidity", 30.0):
            shift_detected = True
            shift_type.append("liquidity")
        
        if shift_detected:
            return {
                "market_id": current.market_id,
                "title": current.title,
                "timestamp": current.timestamp,
                "shift_type": shift_type,
                "changes": changes,
                "current": current.data,
                "previous": previous.data,
            }
        
        return None
    
    def scan_market(
        self,
        market_id: str,
        thresholds: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """Scan a single market for shifts"""
        # Get current snapshot
        current = self.get_market_snapshot(market_id)
        if not current:
            return None
        
        # Get previous snapshot
        previous = self.get_previous_snapshot(market_id)
        
        # Store current snapshot
        self.store_snapshot(current)
        
        # Detect shift
        shift = self.detect_shift(current, previous, thresholds)
        
        if shift:
            # Call callbacks
            for callback in self.shift_callbacks:
                try:
                    callback(shift)
                except Exception as e:
                    print(f"Error in shift callback: {e}")
        
        return shift
    
    def scan_markets(
        self,
        market_ids: List[str],
        thresholds: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Scan multiple markets concurrently"""
        shifts = []
        
        # Use thread pool for concurrent scanning
        futures = []
        for market_id in market_ids:
            future = self.executor.submit(self.scan_market, market_id, thresholds)
            futures.append(future)
        
        # Collect results
        for future in futures:
            try:
                result = future.result(timeout=10)
                if result:
                    shifts.append(result)
            except Exception as e:
                print(f"Error scanning market: {e}")
        
        return shifts
    
    def scan_all_active_markets(self, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """Scan all active markets (uses aggregator for live data with fallback)"""
        try:
            # Use aggregator to get live markets with validation
            markets = self.aggregator.get_live_markets(
                limit=100,
                require_volume=self.require_fresh_data,
                min_volume=0.01
            )
            
            if not markets:
                print("Warning: No live markets found")
                return []
            
            # Validate data freshness
            validation_report = self.aggregator.validate_data_freshness(markets)
            
            if validation_report['stale_markets'] > 0:
                print(f"Warning: {validation_report['stale_markets']} stale markets detected")
            
            if validation_report.get('issues'):
                for issue in validation_report['issues'][:3]:  # Show first 3 issues
                    print(f"  - {issue}")
            
            market_ids = [m.get("id") for m in markets if m.get("id")]
            return self.scan_markets(market_ids, thresholds)
        except Exception as e:
            print(f"Error scanning all markets: {e}")
            return []
    
    def start_monitoring(
        self,
        market_ids: List[str],
        thresholds: Dict[str, float],
    ):
        """Start continuous monitoring loop"""
        self.running = True
        
        while self.running:
            try:
                shifts = self.scan_markets(market_ids, thresholds)
                
                if shifts:
                    print(f"Detected {len(shifts)} shifts at {datetime.now()}")
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Stop monitoring loop"""
        self.running = False
    
    def get_market_history(self, market_id: str, hours: int = 24) -> List[MarketSnapshot]:
        """Get historical snapshots for a market"""
        if market_id not in self.snapshots:
            return []
        
        cutoff_time = time.time() - (hours * 3600)
        return [s for s in self.snapshots[market_id] if s.timestamp >= cutoff_time]
    
    def calculate_volatility(self, market_id: str, window: int = 10) -> float:
        """Calculate volatility (standard deviation of probability changes)"""
        if market_id not in self.snapshots or len(self.snapshots[market_id]) < window:
            return 0.0
        
        recent_snapshots = self.snapshots[market_id][-window:]
        prob_changes = []
        
        for i in range(1, len(recent_snapshots)):
            change = recent_snapshots[i].probability - recent_snapshots[i-1].probability
            prob_changes.append(change)
        
        if not prob_changes:
            return 0.0
        
        # Calculate standard deviation
        mean = sum(prob_changes) / len(prob_changes)
        variance = sum((x - mean) ** 2 for x in prob_changes) / len(prob_changes)
        return variance ** 0.5

