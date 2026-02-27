"""Wallet Cluster Detection

Identifies wallets likely controlled by the same entity based on:
- Timing correlation (trades within seconds of each other)
- Market overlap (trading the same niche markets)
- Size patterns (identical position sizes)
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from collections import defaultdict


class WalletClusterDetector:
    """Detect wallet clusters — groups of wallets controlled by same entity"""

    SIGNALS = [
        'timing_correlation',
        'market_overlap',
        'size_pattern',
    ]

    def __init__(self, database):
        self.db = database

    def _build_timing_lookup(
        self,
        timing_clusters: List[Tuple[str, str, int]],
    ) -> Dict[Tuple[str, str], int]:
        """Convert timing results into O(1) pair lookup map."""
        return {
            tuple(sorted([wallet1, wallet2])): count
            for wallet1, wallet2, count in timing_clusters
        }

    def find_timing_clusters(self, window_seconds=30):
        """Find wallets that consistently trade within seconds of each other.

        Looks at trade timestamps and groups wallets that frequently trade
        within the specified time window.

        Returns list of (wallet1, wallet2, correlation_count) tuples
        """
        trades = self.db.get_recent_trades(hours=168, limit=5000)  # 1 week
        if len(trades) < 2:
            return []

        # Ensure newest->oldest ordering so we can short-circuit once outside window.
        trades = sorted(trades, key=lambda trade: trade.timestamp, reverse=True)

        # Group trades by timestamp windows
        pairs = defaultdict(int)
        for i, t1 in enumerate(trades):
            for t2 in trades[i+1:]:
                delta = (t1.timestamp - t2.timestamp).total_seconds()
                if delta > window_seconds:
                    break
                if t1.wallet_address == t2.wallet_address:
                    continue
                pair = tuple(sorted([t1.wallet_address, t2.wallet_address]))
                pairs[pair] += 1

        # Filter pairs with enough correlated trades (3+)
        results = []
        for (w1, w2), count in pairs.items():
            if count >= 3:
                results.append((w1, w2, count))

        return sorted(results, key=lambda x: x[2], reverse=True)

    def find_market_overlap_clusters(self, min_overlap=0.7):
        """Find wallets trading the same niche markets.

        Calculates Jaccard similarity of market sets between wallets.

        Returns list of (wallet1, wallet2, overlap_score) tuples
        """
        wallets = self.db.get_all_wallets(limit=200)
        if len(wallets) < 2:
            return []

        # Build market sets for each wallet
        wallet_markets = {}
        for wallet in wallets:
            trades = self.db.get_trades_by_wallet(wallet.address, limit=500)
            markets = set(t.market_id for t in trades)
            if len(markets) >= 2:  # Need at least 2 markets for meaningful overlap
                wallet_markets[wallet.address] = markets

        # Compare all pairs
        results = []
        addresses = list(wallet_markets.keys())
        for i, addr1 in enumerate(addresses):
            for addr2 in addresses[i+1:]:
                markets1 = wallet_markets[addr1]
                markets2 = wallet_markets[addr2]

                intersection = markets1 & markets2
                union = markets1 | markets2

                if not union:
                    continue

                overlap = len(intersection) / len(union)
                if overlap >= min_overlap:
                    results.append((addr1, addr2, round(overlap, 3)))

        return sorted(results, key=lambda x: x[2], reverse=True)

    def find_size_pattern_clusters(self):
        """Find wallets using identical position sizes.

        Wallets controlled by the same entity often use round numbers
        or identical trade sizes across accounts.

        Returns list of (wallet1, wallet2, matching_sizes_count) tuples
        """
        wallets = self.db.get_all_wallets(limit=200)
        if len(wallets) < 2:
            return []

        # Build size profiles
        wallet_sizes = {}
        for wallet in wallets:
            trades = self.db.get_trades_by_wallet(wallet.address, limit=200)
            sizes = [round(t.size, 2) for t in trades if t.size > 0]
            if sizes:
                wallet_sizes[wallet.address] = sizes

        # Compare size profiles
        results = []
        addresses = list(wallet_sizes.keys())
        for i, addr1 in enumerate(addresses):
            for addr2 in addresses[i+1:]:
                sizes1 = set(wallet_sizes[addr1])
                sizes2 = set(wallet_sizes[addr2])

                common = sizes1 & sizes2
                if len(common) >= 3:  # At least 3 matching sizes
                    results.append((addr1, addr2, len(common)))

        return sorted(results, key=lambda x: x[2], reverse=True)

    def calculate_cluster_score(
        self,
        wallet1,
        wallet2,
        timing_lookup: Optional[Dict[Tuple[str, str], int]] = None,
    ):
        """Score 0-100 likelihood that two wallets are same entity.

        Combines all detection signals into a single confidence score.
        """
        score = 0
        signals = []

        # Timing correlation (up to 40 points)
        if timing_lookup is None:
            timing_lookup = self._build_timing_lookup(
                self.find_timing_clusters(window_seconds=30)
            )

        pair = tuple(sorted([wallet1, wallet2]))
        timing_count = timing_lookup.get(pair, 0)
        if timing_count:
            timing_score = min(timing_count * 10, 40)
            score += timing_score
            signals.append(f"timing:{timing_count}")

        # Market overlap (up to 35 points)
        w1_trades = self.db.get_trades_by_wallet(wallet1, limit=500)
        w2_trades = self.db.get_trades_by_wallet(wallet2, limit=500)

        markets1 = set(t.market_id for t in w1_trades)
        markets2 = set(t.market_id for t in w2_trades)

        if markets1 and markets2:
            overlap = len(markets1 & markets2) / len(markets1 | markets2)
            overlap_score = int(overlap * 35)
            score += overlap_score
            if overlap_score > 0:
                signals.append(f"overlap:{overlap:.1%}")

        # Size pattern (up to 25 points)
        sizes1 = set(round(t.size, 2) for t in w1_trades if t.size > 0)
        sizes2 = set(round(t.size, 2) for t in w2_trades if t.size > 0)
        common_sizes = sizes1 & sizes2
        if len(common_sizes) >= 2:
            size_score = min(len(common_sizes) * 5, 25)
            score += size_score
            signals.append(f"sizes:{len(common_sizes)}")

        return {
            'score': min(score, 100),
            'signals': signals,
            'risk': 'high' if score >= 70 else 'medium' if score >= 40 else 'low',
        }

    def detect_clusters(self, min_score=60):
        """Run all detection methods, return grouped clusters.

        Returns list of cluster dicts with wallets and confidence scores.
        """
        # Get all wallet pairs from each method
        all_pairs = set()

        timing = self.find_timing_clusters()
        timing_lookup = self._build_timing_lookup(timing)
        for w1, w2, _ in timing:
            all_pairs.add(tuple(sorted([w1, w2])))

        overlap = self.find_market_overlap_clusters()
        for w1, w2, _ in overlap:
            all_pairs.add(tuple(sorted([w1, w2])))

        size = self.find_size_pattern_clusters()
        for w1, w2, _ in size:
            all_pairs.add(tuple(sorted([w1, w2])))

        # Score each pair
        clusters = []
        for w1, w2 in all_pairs:
            result = self.calculate_cluster_score(
                w1,
                w2,
                timing_lookup=timing_lookup,
            )
            if result['score'] >= min_score:
                clusters.append({
                    'wallets': [w1, w2],
                    'score': result['score'],
                    'risk': result['risk'],
                    'signals': result['signals'],
                    'detected_at': datetime.now().isoformat(),
                })

        return sorted(clusters, key=lambda x: x['score'], reverse=True)
