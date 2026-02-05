"""
Cross-Market Arbitrage Scanner

Scans for arbitrage opportunities:
1. Within Polymarket (YES + NO < $1.00)
2. Across correlated markets
3. Cross-platform (Polymarket vs Kalshi)
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from ..db.database import Database
from ..db.models import ArbitrageOpportunity
from ..api.gamma import GammaClient
from ..api.clob import CLOBClient


@dataclass
class ArbitrageResult:
    """Arbitrage opportunity result"""
    type: str  # 'intra_market', 'correlated', 'cross_platform'
    market1_id: str
    market2_id: str
    market1_title: str
    market2_title: str
    market1_yes_price: float
    market1_no_price: float
    market2_yes_price: float = 0.0
    market2_no_price: float = 0.0
    spread: float = 0.0
    expected_profit_pct: float = 0.0
    expected_profit_usd: float = 0.0  # for $100 bet
    fees: float = 0.0
    net_profit: float = 0.0
    timestamp: datetime = None
    confidence: str = 'medium'  # low, medium, high

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ArbitrageScanner:
    """
    Scans for arbitrage opportunities across markets.

    Types of arbitrage:
    1. Intra-market: YES + NO prices don't sum to $1.00
    2. Correlated markets: Similar events with price discrepancies
    3. Cross-platform: Polymarket vs Kalshi price differences
    """

    def __init__(
        self,
        database: Database,
        gamma_client: GammaClient,
        clob_client: CLOBClient,
        min_spread: float = 0.025,  # 2.5% minimum spread
        polymarket_fee: float = 0.02,  # 2% winner fee
    ):
        self.db = database
        self.gamma = gamma_client
        self.clob = clob_client
        self.min_spread = min_spread
        self.polymarket_fee = polymarket_fee

        # Cache for market data
        self.market_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 30  # seconds

    def scan_intra_market_arbitrage(
        self,
        markets: List[Dict[str, Any]],
    ) -> List[ArbitrageResult]:
        """
        Scan for arbitrage within single markets (YES + NO < 1.00).

        In a properly priced market, YES + NO should equal $1.00.
        If YES + NO < $0.975, there's a potential arbitrage opportunity.

        Args:
            markets: List of market data from Gamma API

        Returns:
            List of arbitrage opportunities
        """
        opportunities = []

        for event in markets:
            # Events contain nested markets (YES/NO tokens)
            nested_markets = event.get('markets', [])

            for market in nested_markets:
                market_id = market.get('id', market.get('conditionId', ''))
                if not market_id:
                    continue

                # Get prices
                outcome_prices = market.get('outcomePrices', [])
                if isinstance(outcome_prices, str):
                    import json
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except:
                        continue

                if len(outcome_prices) < 2:
                    continue

                try:
                    yes_price = float(outcome_prices[0])
                    no_price = float(outcome_prices[1])
                except (ValueError, IndexError):
                    continue

                # Check for arbitrage
                total = yes_price + no_price

                if total < (1.0 - self.min_spread):
                    # Buying YES + NO costs less than $1, guaranteed profit
                    spread = 1.0 - total
                    gross_profit_pct = (spread / total) * 100

                    # Calculate net profit after fees
                    # You buy both sides for $total, get $1 back
                    # Pay 2% fee on the winning side's profit ($1 payout)
                    fee_on_winning = self.polymarket_fee * 1.0  # fee on $1 payout
                    net_profit = spread - fee_on_winning

                    if net_profit > 0:
                        result = ArbitrageResult(
                            type='intra_market',
                            market1_id=market_id,
                            market2_id=market_id,
                            market1_title=event.get('title', market.get('question', '')),
                            market2_title=event.get('title', market.get('question', '')),
                            market1_yes_price=yes_price,
                            market1_no_price=no_price,
                            spread=spread,
                            expected_profit_pct=gross_profit_pct,
                            expected_profit_usd=net_profit * 100,  # for $100 bet
                            fees=self.polymarket_fee * 100,
                            net_profit=net_profit * 100,
                            confidence='high' if spread > 0.05 else 'medium',
                        )
                        opportunities.append(result)

                        # Store in database
                        self._store_opportunity(result)

        return sorted(opportunities, key=lambda x: x.net_profit, reverse=True)

    def scan_correlated_markets(
        self,
        markets: List[Dict[str, Any]],
        similarity_threshold: float = 0.8,
    ) -> List[ArbitrageResult]:
        """
        Scan for arbitrage between correlated markets.

        Finds markets with similar events but different prices.

        Args:
            markets: List of market data
            similarity_threshold: Minimum similarity for correlation

        Returns:
            List of arbitrage opportunities
        """
        opportunities = []

        # Group markets by category/tags
        category_markets: Dict[str, List[Dict]] = defaultdict(list)

        for event in markets:
            # Get category from tags or title keywords
            tags = event.get('tags', [])
            category = None

            if isinstance(tags, list) and tags:
                category = tags[0].get('label', '') if isinstance(tags[0], dict) else str(tags[0])

            if not category:
                # Extract category from title
                title = event.get('title', '').lower()
                if 'election' in title or 'president' in title:
                    category = 'politics'
                elif 'bitcoin' in title or 'crypto' in title or 'eth' in title:
                    category = 'crypto'
                elif 'trump' in title:
                    category = 'trump'
                elif 'fed' in title or 'rate' in title:
                    category = 'economics'
                else:
                    category = 'other'

            category_markets[category].append(event)

        # Compare markets within same category
        for category, cat_markets in category_markets.items():
            if len(cat_markets) < 2:
                continue

            for i, market1 in enumerate(cat_markets):
                for market2 in cat_markets[i + 1:]:
                    # Check if markets are related
                    similarity = self._calculate_title_similarity(
                        market1.get('title', ''),
                        market2.get('title', ''),
                    )

                    if similarity < similarity_threshold:
                        continue

                    # Get prices
                    m1_prices = self._get_market_prices(market1)
                    m2_prices = self._get_market_prices(market2)

                    if not m1_prices or not m2_prices:
                        continue

                    # Check for price discrepancy
                    price_diff = abs(m1_prices['yes'] - m2_prices['yes'])

                    if price_diff >= self.min_spread:
                        # Arbitrage: buy low, sell high
                        if m1_prices['yes'] < m2_prices['yes']:
                            buy_market = market1
                            sell_market = market2
                            buy_price = m1_prices['yes']
                            sell_price = m2_prices['yes']
                        else:
                            buy_market = market2
                            sell_market = market1
                            buy_price = m2_prices['yes']
                            sell_price = m1_prices['yes']

                        spread = sell_price - buy_price
                        # Fee is percentage-based: pay fee on each side's winnings
                        fee_cost = (sell_price * self.polymarket_fee) + (buy_price * self.polymarket_fee)
                        gross_profit = spread - fee_cost

                        if gross_profit > 0:
                            result = ArbitrageResult(
                                type='correlated',
                                market1_id=buy_market.get('id', ''),
                                market2_id=sell_market.get('id', ''),
                                market1_title=buy_market.get('title', ''),
                                market2_title=sell_market.get('title', ''),
                                market1_yes_price=buy_price,
                                market1_no_price=m1_prices['no'],
                                market2_yes_price=sell_price,
                                market2_no_price=m2_prices['no'],
                                spread=spread,
                                expected_profit_pct=(gross_profit / buy_price) * 100,
                                expected_profit_usd=gross_profit * 100,
                                fees=self.polymarket_fee * 200,
                                net_profit=gross_profit * 100,
                                confidence='low',  # Correlated arb is riskier
                            )
                            opportunities.append(result)

        return sorted(opportunities, key=lambda x: x.net_profit, reverse=True)

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two market titles"""
        # Simple word overlap similarity
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        # Remove common words
        stop_words = {'the', 'a', 'an', 'will', 'be', 'by', 'in', 'on', 'to', 'of', '?'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _get_market_prices(self, event: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract YES/NO prices from market event"""
        nested_markets = event.get('markets', [])
        if not nested_markets:
            return None

        market = nested_markets[0]
        outcome_prices = market.get('outcomePrices', [])

        if isinstance(outcome_prices, str):
            import json
            try:
                outcome_prices = json.loads(outcome_prices)
            except:
                return None

        if len(outcome_prices) < 2:
            return None

        try:
            return {
                'yes': float(outcome_prices[0]),
                'no': float(outcome_prices[1]),
            }
        except (ValueError, IndexError):
            return None

    def _store_opportunity(self, result: ArbitrageResult) -> None:
        """Store arbitrage opportunity in database"""
        arb = ArbitrageOpportunity(
            market1_id=result.market1_id,
            market2_id=result.market2_id,
            market1_title=result.market1_title,
            market2_title=result.market2_title,
            market1_price=result.market1_yes_price,
            market2_price=result.market2_yes_price,
            spread=result.spread,
            expected_profit=result.net_profit,
            timestamp=result.timestamp,
            status='open',
        )
        self.db.insert_arbitrage(arb)

    async def scan_all(self) -> Dict[str, List[ArbitrageResult]]:
        """
        Run all arbitrage scans.

        Returns:
            Dict with results by type
        """
        # Get current markets
        markets = self.gamma.get_markets(limit=100, active=True, closed=False)

        results = {
            'intra_market': self.scan_intra_market_arbitrage(markets),
            'correlated': self.scan_correlated_markets(markets),
        }

        return results

    def get_best_opportunities(self, limit: int = 10) -> List[ArbitrageResult]:
        """Get best current arbitrage opportunities"""
        all_results = []

        markets = self.gamma.get_markets(limit=100, active=True, closed=False)
        all_results.extend(self.scan_intra_market_arbitrage(markets))
        all_results.extend(self.scan_correlated_markets(markets))

        return sorted(all_results, key=lambda x: x.net_profit, reverse=True)[:limit]

    def format_opportunity(self, arb: ArbitrageResult) -> str:
        """Format arbitrage opportunity for display"""
        lines = []

        if arb.type == 'intra_market':
            lines.append(f"[Intra-Market Arbitrage]")
            lines.append(f"Market: {arb.market1_title[:60]}")
            lines.append(f"YES: ${arb.market1_yes_price:.2f} + NO: ${arb.market1_no_price:.2f} = ${arb.market1_yes_price + arb.market1_no_price:.2f}")
        else:
            lines.append(f"[{arb.type.replace('_', ' ').title()}]")
            lines.append(f"Buy: {arb.market1_title[:40]} @ ${arb.market1_yes_price:.2f}")
            lines.append(f"Sell: {arb.market2_title[:40]} @ ${arb.market2_yes_price:.2f}")

        lines.append(f"Spread: {arb.spread:.1%}")
        lines.append(f"Expected Profit: ${arb.net_profit:.2f} (on $100 bet)")
        lines.append(f"Confidence: {arb.confidence}")

        return "\n".join(lines)


class KalshiArbitrageScanner:
    """
    Cross-platform arbitrage scanner for Polymarket vs Kalshi.

    Requires Kalshi API access.
    """

    def __init__(
        self,
        database: Database,
        gamma_client: GammaClient,
        kalshi_api_key: str = "",
        kalshi_base_url: str = "https://trading-api.kalshi.com/trade-api/v2",
        polymarket_fee: float = 0.02,
        kalshi_fee: float = 0.007,
    ):
        self.db = database
        self.gamma = gamma_client
        self.kalshi_api_key = kalshi_api_key
        self.kalshi_base_url = kalshi_base_url
        self.polymarket_fee = polymarket_fee
        self.kalshi_fee = kalshi_fee

        # Market matching cache
        self.market_matches: Dict[str, str] = {}  # PM market_id -> Kalshi ticker

    def get_kalshi_markets(self) -> List[Dict[str, Any]]:
        """Fetch markets from Kalshi API"""
        if not self.kalshi_api_key:
            return []

        import requests

        try:
            headers = {
                'Authorization': f'Bearer {self.kalshi_api_key}',
                'Content-Type': 'application/json',
            }

            response = requests.get(
                f"{self.kalshi_base_url}/markets",
                headers=headers,
                params={'status': 'open', 'limit': 100},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('markets', [])
            else:
                print(f"Kalshi API error: {response.status_code}")
                return []

        except Exception as e:
            print(f"Error fetching Kalshi markets: {e}")
            return []

    def match_markets(
        self,
        pm_markets: List[Dict[str, Any]],
        kalshi_markets: List[Dict[str, Any]],
    ) -> List[Tuple[Dict, Dict, float]]:
        """
        Match Polymarket markets to Kalshi markets.

        Returns list of (pm_market, kalshi_market, similarity_score) tuples.
        """
        matches = []

        for pm_event in pm_markets:
            pm_title = pm_event.get('title', '').lower()

            for kalshi in kalshi_markets:
                kalshi_title = kalshi.get('title', kalshi.get('ticker', '')).lower()

                # Calculate similarity
                similarity = self._calculate_match_score(pm_title, kalshi_title)

                if similarity >= 0.7:
                    matches.append((pm_event, kalshi, similarity))

        # Sort by similarity
        return sorted(matches, key=lambda x: x[2], reverse=True)

    def _calculate_match_score(self, title1: str, title2: str) -> float:
        """Calculate match score between two market titles"""
        # Extract key terms
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        # Remove common words
        stop_words = {'the', 'a', 'an', 'will', 'be', 'by', 'in', 'on', 'to', 'of', '?', '-', 'yes', 'no'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        base_score = len(intersection) / len(union) if union else 0.0

        # Boost for key term matches
        key_terms = ['trump', 'biden', 'election', 'bitcoin', 'fed', 'rate', 'president']
        for term in key_terms:
            if term in title1 and term in title2:
                base_score = min(1.0, base_score + 0.2)

        return base_score

    def scan_cross_platform_arbitrage(
        self,
        min_spread: float = 0.03,
    ) -> List[ArbitrageResult]:
        """
        Scan for cross-platform arbitrage opportunities.

        Args:
            min_spread: Minimum spread required (default 3%)

        Returns:
            List of arbitrage opportunities
        """
        if not self.kalshi_api_key:
            return []

        opportunities = []

        # Get markets from both platforms
        pm_markets = self.gamma.get_markets(limit=100, active=True, closed=False)
        kalshi_markets = self.get_kalshi_markets()

        if not kalshi_markets:
            return []

        # Find matching markets
        matches = self.match_markets(pm_markets, kalshi_markets)

        for pm_event, kalshi, similarity in matches:
            # Get Polymarket price
            pm_prices = self._get_pm_prices(pm_event)
            if not pm_prices:
                continue

            # Get Kalshi price
            kalshi_price = kalshi.get('yes_bid', kalshi.get('last_price', 0))
            if not kalshi_price:
                continue

            # Calculate spread
            price_diff = abs(pm_prices['yes'] - kalshi_price)

            if price_diff >= min_spread:
                # Determine direction
                if pm_prices['yes'] < kalshi_price:
                    buy_platform = 'Polymarket'
                    sell_platform = 'Kalshi'
                    buy_price = pm_prices['yes']
                    sell_price = kalshi_price
                else:
                    buy_platform = 'Kalshi'
                    sell_platform = 'Polymarket'
                    buy_price = kalshi_price
                    sell_price = pm_prices['yes']

                # Calculate profit after fees
                total_fees = self.polymarket_fee + self.kalshi_fee
                gross_profit = price_diff - total_fees

                if gross_profit > 0:
                    result = ArbitrageResult(
                        type='cross_platform',
                        market1_id=pm_event.get('id', ''),
                        market2_id=kalshi.get('ticker', ''),
                        market1_title=f"[{buy_platform}] {pm_event.get('title', '')[:40]}",
                        market2_title=f"[{sell_platform}] {kalshi.get('title', '')[:40]}",
                        market1_yes_price=buy_price,
                        market1_no_price=pm_prices.get('no', 1 - buy_price),
                        market2_yes_price=sell_price,
                        market2_no_price=1 - sell_price,
                        spread=price_diff,
                        expected_profit_pct=(gross_profit / buy_price) * 100,
                        expected_profit_usd=gross_profit * 100,
                        fees=total_fees * 100,
                        net_profit=gross_profit * 100,
                        confidence='medium' if similarity > 0.85 else 'low',
                    )
                    opportunities.append(result)

        return sorted(opportunities, key=lambda x: x.net_profit, reverse=True)

    def _get_pm_prices(self, event: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract prices from Polymarket event"""
        nested_markets = event.get('markets', [])
        if not nested_markets:
            return None

        market = nested_markets[0]
        outcome_prices = market.get('outcomePrices', [])

        if isinstance(outcome_prices, str):
            import json
            try:
                outcome_prices = json.loads(outcome_prices)
            except:
                return None

        if len(outcome_prices) < 2:
            return None

        try:
            return {
                'yes': float(outcome_prices[0]),
                'no': float(outcome_prices[1]),
            }
        except (ValueError, IndexError):
            return None
