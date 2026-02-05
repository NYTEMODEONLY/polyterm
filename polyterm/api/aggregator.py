"""API Data Aggregator with fallback and validation"""

from typing import Dict, List, Optional, Any
import logging

from .gamma import GammaClient
from .clob import CLOBClient
from .subgraph import SubgraphClient

logger = logging.getLogger(__name__)


class APIAggregator:
    """Aggregates data from multiple PolyMarket API sources with fallback"""
    
    def __init__(
        self,
        gamma_client: GammaClient,
        clob_client: CLOBClient,
        subgraph_client: SubgraphClient,
    ):
        self.gamma_client = gamma_client
        self.clob_client = clob_client
        self.subgraph_client = subgraph_client
    
    def get_live_markets(
        self,
        limit: int = 100,
        require_volume: bool = True,
        min_volume: float = 0.01,
    ) -> List[Dict[str, Any]]:
        """Get live markets with automatic fallback
        
        Tries multiple sources in order:
        1. Gamma API /events (has volume data)
        2. CLOB sampling-markets (fallback if Gamma fails)
        
        Args:
            limit: Maximum markets to return
            require_volume: Require volume data
            min_volume: Minimum volume threshold
        
        Returns:
            List of live market dictionaries
        """
        # Try Gamma API first (primary - has volume)
        try:
            markets = self.gamma_client.get_markets(limit=limit, active=True, closed=False)
            
            # Filter for fresh markets only
            fresh_markets = self.gamma_client.filter_fresh_markets(
                markets,
                max_age_hours=24,
                require_volume=require_volume,
                min_volume=min_volume,
            )
            
            if fresh_markets:
                logger.info(f"Retrieved {len(fresh_markets)} live markets from Gamma API")
                return fresh_markets
            else:
                logger.warning("Gamma API returned no fresh markets")
        except Exception as e:
            logger.error(f"Gamma API failed: {e}")
        
        # Fallback to CLOB sampling-markets
        try:
            markets = self.clob_client.get_current_markets(limit=limit)
            
            # Filter for current markets
            current_markets = [m for m in markets if self.clob_client.is_market_current(m)]
            
            if current_markets:
                logger.info(f"Retrieved {len(current_markets)} markets from CLOB fallback")
                if require_volume:
                    logger.warning("CLOB markets may lack volume data, returning anyway as fallback")
                return current_markets
        except Exception as e:
            logger.error(f"CLOB API failed: {e}")
        
        # If both fail, return empty list
        logger.error("All API sources failed to return live markets")
        return []
    
    def enrich_market_data(
        self,
        market_id: str,
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich market data by combining info from multiple sources
        
        Args:
            market_id: Market ID
            base_data: Base market data
        
        Returns:
            Enriched market dictionary
        """
        enriched = base_data.copy()
        
        # Try to add volume from Gamma if missing
        if 'volume' not in enriched or enriched.get('volume', 0) == 0:
            try:
                gamma_market = self.gamma_client.get_market(market_id)
                if gamma_market:
                    enriched['volume'] = gamma_market.get('volume', 0)
                    enriched['volume24hr'] = gamma_market.get('volume24hr', 0)
            except Exception:
                pass
        
        # Try to add order book data from CLOB
        try:
            order_book = self.clob_client.get_order_book(market_id)
            if order_book:
                enriched['order_book'] = order_book
                enriched['spread'] = self.clob_client.calculate_spread(order_book)
        except Exception:
            pass
        
        # Try to add on-chain stats from Subgraph
        try:
            stats = self.subgraph_client.get_market_statistics(market_id)
            if stats:
                enriched['on_chain_volume'] = stats.get('totalVolume', 0)
                enriched['trade_count'] = stats.get('tradeCount', 0)
        except Exception:
            pass
        
        # Add data source metadata
        enriched['_data_sources'] = []
        if 'volume' in enriched and enriched['volume']:
            enriched['_data_sources'].append('gamma')
        if 'order_book' in enriched:
            enriched['_data_sources'].append('clob')
        if 'on_chain_volume' in enriched:
            enriched['_data_sources'].append('subgraph')
        
        return enriched
    
    def get_top_markets_by_volume(
        self,
        limit: int = 10,
        min_volume: float = 100,
    ) -> List[Dict[str, Any]]:
        """Get top markets sorted by 24hr volume

        Args:
            limit: Number of markets to return
            min_volume: Minimum 24hr volume

        Returns:
            List of top markets sorted by volume
        """
        # Request more markets to account for filtering (5x to be safe)
        markets = self.get_live_markets(limit=max(limit * 5, 100), require_volume=True, min_volume=min_volume)
        
        # Sort by 24hr volume
        sorted_markets = sorted(
            markets,
            key=lambda m: float(m.get('volume24hr', 0) or 0),
            reverse=True
        )
        
        return sorted_markets[:limit]
    
    def validate_data_freshness(self, markets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate freshness of market data
        
        Args:
            markets: List of markets to validate
        
        Returns:
            Validation report
        """
        from datetime import datetime
        
        report = {
            'total_markets': len(markets),
            'fresh_markets': 0,
            'stale_markets': 0,
            'markets_with_volume': 0,
            'oldest_market_year': datetime.now().year,
            'issues': []
        }
        
        for market in markets:
            # Check freshness
            is_fresh = self.gamma_client.is_market_fresh(market, max_age_hours=24)
            
            if is_fresh:
                report['fresh_markets'] += 1
            else:
                report['stale_markets'] += 1
                report['issues'].append(f"Stale market: {market.get('question', 'Unknown')[:50]}")
            
            # Check volume
            volume = float(market.get('volume', 0) or 0)
            volume_24hr = float(market.get('volume24hr', 0) or 0)
            
            if volume > 0 or volume_24hr > 0:
                report['markets_with_volume'] += 1
            
            # Track oldest year
            try:
                end_date = market.get('endDate', '')
                if end_date and len(end_date) >= 4:
                    year = int(end_date[:4])
                    if year < report['oldest_market_year']:
                        report['oldest_market_year'] = year
            except Exception:
                pass
        
        # Add warnings
        if report['stale_markets'] > report['fresh_markets']:
            report['issues'].append("WARNING: More stale markets than fresh markets!")
        
        if report['markets_with_volume'] == 0:
            report['issues'].append("CRITICAL: No markets have volume data!")
        
        return report

