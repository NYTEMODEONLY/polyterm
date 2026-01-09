"""
Market Correlation Engine

Features:
- Calculate rolling correlations between markets
- Alert on correlation breaks
- Cluster analysis of related markets
- Category-based correlation heatmaps
"""

import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

from ..db.database import Database
from ..db.models import MarketSnapshot
from ..api.gamma import GammaClient


@dataclass
class CorrelationResult:
    """Correlation between two markets"""
    market1_id: str
    market2_id: str
    market1_title: str
    market2_title: str
    correlation: float  # -1 to 1
    sample_size: int
    time_window_hours: int
    calculated_at: datetime = field(default_factory=datetime.now)

    @property
    def strength(self) -> str:
        """Human-readable correlation strength"""
        abs_corr = abs(self.correlation)
        if abs_corr >= 0.8:
            return 'very_strong'
        elif abs_corr >= 0.6:
            return 'strong'
        elif abs_corr >= 0.4:
            return 'moderate'
        elif abs_corr >= 0.2:
            return 'weak'
        else:
            return 'negligible'

    @property
    def direction(self) -> str:
        """Correlation direction"""
        if self.correlation > 0.1:
            return 'positive'
        elif self.correlation < -0.1:
            return 'negative'
        else:
            return 'neutral'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'market1_id': self.market1_id,
            'market2_id': self.market2_id,
            'market1_title': self.market1_title,
            'market2_title': self.market2_title,
            'correlation': self.correlation,
            'strength': self.strength,
            'direction': self.direction,
            'sample_size': self.sample_size,
            'time_window_hours': self.time_window_hours,
            'calculated_at': self.calculated_at.isoformat(),
        }


@dataclass
class MarketCluster:
    """Group of correlated markets"""
    cluster_id: int
    markets: List[str]  # Market IDs
    market_titles: List[str]
    avg_correlation: float
    category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cluster_id': self.cluster_id,
            'markets': self.markets,
            'market_titles': self.market_titles,
            'market_count': len(self.markets),
            'avg_correlation': self.avg_correlation,
            'category': self.category,
        }


class CorrelationEngine:
    """
    Calculates and monitors correlations between prediction markets.
    """

    def __init__(
        self,
        database: Database,
        gamma_client: Optional[GammaClient] = None,
    ):
        self.db = database
        self.gamma = gamma_client

        # Cache for market data
        self._price_cache: Dict[str, List[Tuple[datetime, float]]] = {}
        self._cache_ttl = 300  # 5 minutes

    def calculate_correlation(
        self,
        market1_id: str,
        market2_id: str,
        hours: int = 24,
    ) -> Optional[CorrelationResult]:
        """
        Calculate correlation between two markets.

        Uses Pearson correlation coefficient on price time series.

        Args:
            market1_id: First market ID
            market2_id: Second market ID
            hours: Time window in hours

        Returns:
            CorrelationResult or None if insufficient data
        """
        # Get price series for both markets
        prices1 = self._get_price_series(market1_id, hours)
        prices2 = self._get_price_series(market2_id, hours)

        if len(prices1) < 5 or len(prices2) < 5:
            return None

        # Align time series
        aligned = self._align_series(prices1, prices2)

        if len(aligned) < 5:
            return None

        # Extract aligned prices
        p1 = [x[1] for x in aligned]
        p2 = [x[2] for x in aligned]

        # Calculate Pearson correlation
        correlation = self._pearson_correlation(p1, p2)

        # Get market titles
        title1 = self._get_market_title(market1_id)
        title2 = self._get_market_title(market2_id)

        return CorrelationResult(
            market1_id=market1_id,
            market2_id=market2_id,
            market1_title=title1,
            market2_title=title2,
            correlation=correlation,
            sample_size=len(aligned),
            time_window_hours=hours,
        )

    def _get_price_series(
        self,
        market_id: str,
        hours: int,
    ) -> List[Tuple[datetime, float]]:
        """Get time series of prices for a market"""
        # Try database first
        snapshots = self.db.get_market_history(market_id, hours=hours)

        if snapshots:
            return [(s.timestamp, s.probability) for s in snapshots]

        # No data available
        return []

    def _align_series(
        self,
        series1: List[Tuple[datetime, float]],
        series2: List[Tuple[datetime, float]],
        tolerance_minutes: int = 15,
    ) -> List[Tuple[datetime, float, float]]:
        """
        Align two time series by matching timestamps.

        Args:
            series1: First series
            series2: Second series
            tolerance_minutes: Maximum time difference for matching

        Returns:
            List of (timestamp, price1, price2) tuples
        """
        aligned = []
        tolerance = timedelta(minutes=tolerance_minutes)

        # Create lookup for series2
        s2_dict = {ts: price for ts, price in series2}
        s2_times = sorted(s2_dict.keys())

        for ts1, price1 in series1:
            # Find closest timestamp in series2
            best_match = None
            best_diff = tolerance

            for ts2 in s2_times:
                diff = abs(ts1 - ts2)
                if diff < best_diff:
                    best_diff = diff
                    best_match = ts2

            if best_match is not None:
                aligned.append((ts1, price1, s2_dict[best_match]))

        return aligned

    def _pearson_correlation(
        self,
        x: List[float],
        y: List[float],
    ) -> float:
        """
        Calculate Pearson correlation coefficient.

        Args:
            x: First series
            y: Second series

        Returns:
            Correlation coefficient (-1 to 1)
        """
        n = len(x)
        if n == 0 or len(y) != n:
            return 0.0

        # Calculate means
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        # Calculate covariance and standard deviations
        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)

        if std_x == 0 or std_y == 0:
            return 0.0

        return cov / (std_x * std_y)

    def _get_market_title(self, market_id: str) -> str:
        """Get market title from cache or API"""
        if self.gamma:
            try:
                # This is a simplified lookup
                return market_id[:30]
            except:
                pass
        return market_id

    def find_correlated_markets(
        self,
        market_id: str,
        min_correlation: float = 0.5,
        max_results: int = 10,
        hours: int = 24,
    ) -> List[CorrelationResult]:
        """
        Find markets correlated with a given market.

        Args:
            market_id: Target market
            min_correlation: Minimum absolute correlation
            max_results: Maximum results to return
            hours: Time window

        Returns:
            List of correlation results sorted by correlation strength
        """
        correlations = []

        # Get all markets with snapshot data
        all_snapshots = self.db.get_market_history(market_id, hours=hours * 24)

        # Get unique market IDs from database
        # In a real implementation, we'd query for all markets
        market_ids = set()
        # This is a placeholder - in production you'd get all tracked markets

        for other_id in market_ids:
            if other_id == market_id:
                continue

            result = self.calculate_correlation(market_id, other_id, hours)
            if result and abs(result.correlation) >= min_correlation:
                correlations.append(result)

        # Sort by absolute correlation
        correlations.sort(key=lambda x: abs(x.correlation), reverse=True)

        return correlations[:max_results]

    def calculate_correlation_matrix(
        self,
        market_ids: List[str],
        hours: int = 24,
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate correlation matrix for multiple markets.

        Args:
            market_ids: List of market IDs
            hours: Time window

        Returns:
            Nested dict of correlations: {market1: {market2: correlation}}
        """
        matrix: Dict[str, Dict[str, float]] = defaultdict(dict)

        for i, m1 in enumerate(market_ids):
            matrix[m1][m1] = 1.0  # Self-correlation

            for m2 in market_ids[i + 1:]:
                result = self.calculate_correlation(m1, m2, hours)
                if result:
                    matrix[m1][m2] = result.correlation
                    matrix[m2][m1] = result.correlation
                else:
                    matrix[m1][m2] = 0.0
                    matrix[m2][m1] = 0.0

        return dict(matrix)

    def find_market_clusters(
        self,
        market_ids: List[str],
        min_correlation: float = 0.6,
        hours: int = 24,
    ) -> List[MarketCluster]:
        """
        Group markets into clusters based on correlation.

        Uses simple connected components algorithm.

        Args:
            market_ids: Markets to cluster
            min_correlation: Minimum correlation to consider related
            hours: Time window

        Returns:
            List of market clusters
        """
        # Calculate correlation matrix
        matrix = self.calculate_correlation_matrix(market_ids, hours)

        # Build adjacency graph
        graph: Dict[str, set] = defaultdict(set)

        for m1 in market_ids:
            for m2 in market_ids:
                if m1 != m2:
                    corr = matrix.get(m1, {}).get(m2, 0)
                    if abs(corr) >= min_correlation:
                        graph[m1].add(m2)
                        graph[m2].add(m1)

        # Find connected components (clusters)
        visited = set()
        clusters = []
        cluster_id = 0

        for market in market_ids:
            if market in visited:
                continue

            # BFS to find all connected markets
            cluster_markets = []
            queue = [market]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue

                visited.add(current)
                cluster_markets.append(current)

                for neighbor in graph[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            if cluster_markets:
                # Calculate average correlation within cluster
                correlations = []
                for i, m1 in enumerate(cluster_markets):
                    for m2 in cluster_markets[i + 1:]:
                        corr = matrix.get(m1, {}).get(m2, 0)
                        correlations.append(abs(corr))

                avg_corr = sum(correlations) / len(correlations) if correlations else 0

                clusters.append(MarketCluster(
                    cluster_id=cluster_id,
                    markets=cluster_markets,
                    market_titles=[self._get_market_title(m) for m in cluster_markets],
                    avg_correlation=avg_corr,
                ))
                cluster_id += 1

        return clusters

    def detect_correlation_breaks(
        self,
        market1_id: str,
        market2_id: str,
        short_window: int = 6,
        long_window: int = 72,
        threshold: float = 0.3,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect when correlation between markets breaks down.

        Compares short-term vs long-term correlation.

        Args:
            market1_id: First market
            market2_id: Second market
            short_window: Short-term window (hours)
            long_window: Long-term window (hours)
            threshold: Minimum difference to trigger alert

        Returns:
            Break detection result or None
        """
        short_corr = self.calculate_correlation(market1_id, market2_id, short_window)
        long_corr = self.calculate_correlation(market1_id, market2_id, long_window)

        if not short_corr or not long_corr:
            return None

        diff = short_corr.correlation - long_corr.correlation

        if abs(diff) >= threshold:
            return {
                'market1_id': market1_id,
                'market2_id': market2_id,
                'short_term_correlation': short_corr.correlation,
                'long_term_correlation': long_corr.correlation,
                'difference': diff,
                'direction': 'strengthening' if diff > 0 else 'weakening',
                'alert': True,
                'message': f"Correlation {'strengthened' if diff > 0 else 'weakened'} by {abs(diff):.2f}",
            }

        return {
            'alert': False,
            'short_term_correlation': short_corr.correlation,
            'long_term_correlation': long_corr.correlation,
            'difference': diff,
        }

    def render_heatmap_ascii(
        self,
        market_ids: List[str],
        hours: int = 24,
        width: int = 60,
    ) -> str:
        """
        Render correlation matrix as ASCII heatmap.

        Args:
            market_ids: Markets to include
            hours: Time window
            width: Display width

        Returns:
            ASCII art heatmap
        """
        if len(market_ids) < 2:
            return "Need at least 2 markets for correlation matrix"

        matrix = self.calculate_correlation_matrix(market_ids, hours)

        # Truncate market IDs for display
        max_label_len = 10
        labels = [m[:max_label_len] for m in market_ids]

        lines = []
        lines.append("Correlation Heatmap")
        lines.append("=" * width)
        lines.append("")

        # Header row
        header = " " * (max_label_len + 2)
        for label in labels:
            header += f"{label[:3]:^5}"
        lines.append(header)

        # Correlation symbols
        def corr_symbol(c: float) -> str:
            if c >= 0.8:
                return "+++"
            elif c >= 0.5:
                return "++"
            elif c >= 0.2:
                return "+"
            elif c <= -0.8:
                return "---"
            elif c <= -0.5:
                return "--"
            elif c <= -0.2:
                return "-"
            else:
                return "."

        # Matrix rows
        for i, m1 in enumerate(market_ids):
            row = f"{labels[i]:<{max_label_len}}  "
            for m2 in market_ids:
                corr = matrix.get(m1, {}).get(m2, 0)
                row += f"{corr_symbol(corr):^5}"
            lines.append(row)

        lines.append("")
        lines.append("Legend: +++ (>0.8) ++ (>0.5) + (>0.2) . (neutral) - (<-0.2) -- (<-0.5) --- (<-0.8)")

        return "\n".join(lines)
