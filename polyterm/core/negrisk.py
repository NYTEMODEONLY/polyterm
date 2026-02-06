"""NegRisk Multi-Outcome Arbitrage Detection

Detects arbitrage in multi-outcome (NegRisk) markets where the sum of all
outcome YES prices doesn't equal $1.00.

In NegRisk markets, multiple outcomes are mutually exclusive (e.g., "Who wins
the election?" with 5+ candidates). The sum of all YES prices should be $1.00.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..api.gamma import GammaClient
from ..api.clob import CLOBClient
from ..utils.json_output import safe_float


class NegRiskAnalyzer:
    """Analyze multi-outcome NegRisk markets for arbitrage"""

    def __init__(self, gamma_client, clob_client=None, polymarket_fee=0.02):
        self.gamma = gamma_client
        self.clob = clob_client
        self.polymarket_fee = polymarket_fee

    def find_multi_outcome_events(self, limit=50):
        """Find events with 3+ outcome markets (NegRisk candidates)

        Returns list of events that have 3+ markets (multi-outcome)
        """
        events = self.gamma.get_markets(limit=limit * 3, active=True, closed=False)
        multi = []
        for event in events:
            markets = event.get('markets', [])
            if len(markets) >= 3:
                multi.append(event)
            if len(multi) >= limit:
                break
        return multi

    def analyze_event(self, event):
        """Analyze a multi-outcome event for NegRisk arbitrage

        NegRisk property: In a complete set of mutually exclusive outcomes,
        the sum of all YES prices should equal $1.00.
        If sum < $1.00: buy all outcomes (guaranteed profit on resolution)
        If sum > $1.00: overpriced (potential short opportunity)
        """
        markets = event.get('markets', [])
        if len(markets) < 2:
            return None

        outcomes = []
        total_yes = 0.0

        for market in markets:
            outcome_prices = market.get('outcomePrices', [])
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except Exception:
                    continue

            if not outcome_prices:
                continue

            yes_price = safe_float(outcome_prices[0])
            question = market.get('question', market.get('groupItemTitle', ''))
            token_id = market.get('clobTokenIds', [''])[0] if isinstance(market.get('clobTokenIds', []), list) else ''
            if isinstance(market.get('clobTokenIds', ''), str):
                try:
                    ids = json.loads(market.get('clobTokenIds', '[]'))
                    token_id = ids[0] if ids else ''
                except Exception:
                    token_id = ''

            outcomes.append({
                'question': question[:60],
                'yes_price': yes_price,
                'market_id': market.get('id', market.get('conditionId', '')),
                'token_id': token_id,
            })
            total_yes += yes_price

        if not outcomes:
            return None

        spread = abs(1.0 - total_yes)

        # Calculate fee-adjusted profit for underpriced case
        # Buy all YES outcomes for $total_yes, get $1.00 back guaranteed
        # Fee: 2% on winnings of the ONE outcome that resolves YES
        # Winning = 1.0 - cheapest_outcome_price (worst case for fees)
        cheapest = min(o['yes_price'] for o in outcomes) if outcomes else 0
        fee_on_winning = self.polymarket_fee * (1.0 - cheapest) if cheapest < 1.0 else 0

        if total_yes < 1.0:
            net_profit = (1.0 - total_yes) - fee_on_winning
        else:
            net_profit = -(total_yes - 1.0)  # Loss if overpriced

        return {
            'event_title': event.get('title', ''),
            'event_id': event.get('id', ''),
            'num_outcomes': len(outcomes),
            'total_yes_price': round(total_yes, 4),
            'spread': round(spread, 4),
            'type': 'underpriced' if total_yes < 1.0 else 'overpriced',
            'fee_adjusted_profit': round(net_profit, 4),
            'profit_per_100': round(net_profit * 100, 2),
            'outcomes': outcomes,
            'timestamp': datetime.now().isoformat(),
        }

    def scan_all(self, min_spread=0.02):
        """Scan all NegRisk events for arbitrage opportunities

        Args:
            min_spread: Minimum spread threshold (default 2%)

        Returns:
            List of arbitrage opportunities sorted by profit potential
        """
        events = self.find_multi_outcome_events(limit=50)
        opportunities = []

        for event in events:
            result = self.analyze_event(event)
            if result and result['spread'] >= min_spread:
                opportunities.append(result)

        return sorted(opportunities, key=lambda x: x['fee_adjusted_profit'], reverse=True)
