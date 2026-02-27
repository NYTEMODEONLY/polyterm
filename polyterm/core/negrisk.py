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

    def _extract_event_reference(self, market):
        """Extract event key and metadata from a flat market row."""
        event_data = {}
        events = market.get("events")
        if isinstance(events, list) and events:
            first_event = events[0]
            if isinstance(first_event, dict):
                event_data = first_event
        elif isinstance(market.get("event"), dict):
            event_data = market.get("event", {})

        event_key = (
            event_data.get("id")
            or market.get("eventId")
            or market.get("event_id")
            or event_data.get("slug")
            or market.get("eventSlug")
            or market.get("event_slug")
        )

        if event_key is None:
            return None, {}

        return str(event_key), event_data

    def _extract_token_id(self, market):
        """Extract first CLOB token id safely from list or JSON string."""
        token_ids = market.get("clobTokenIds", [])
        if isinstance(token_ids, list):
            return str(token_ids[0]) if token_ids else ""
        if isinstance(token_ids, str):
            try:
                parsed = json.loads(token_ids)
            except Exception:
                return ""
            if isinstance(parsed, list) and parsed:
                return str(parsed[0])
        return ""

    def find_multi_outcome_events(self, limit=50):
        """Find events with 3+ outcome markets (NegRisk candidates)

        Returns list of events that have 3+ markets (multi-outcome)
        """
        rows = self.gamma.get_markets(limit=limit * 3, active=True, closed=False)
        multi = []

        # Backward-compatible path for callers/tests that already pass nested
        # event payloads with `event["markets"]`.
        for event in rows:
            markets = event.get('markets', [])
            if isinstance(markets, list) and len(markets) >= 3:
                multi.append(event)
            if len(multi) >= limit:
                return multi

        # Production Gamma `/markets` payload is flat: group markets by event.
        grouped_events = {}
        for market in rows:
            if not isinstance(market, dict):
                continue
            if isinstance(market.get("markets"), list):
                continue

            event_key, event_data = self._extract_event_reference(market)
            if event_key is None:
                continue

            if event_key not in grouped_events:
                grouped_events[event_key] = {
                    "id": event_data.get("id")
                    or market.get("eventId")
                    or market.get("event_id")
                    or event_key,
                    "title": event_data.get("title")
                    or market.get("eventTitle")
                    or market.get("event_title")
                    or market.get("title")
                    or market.get("question", ""),
                    "markets": [],
                }

            grouped_events[event_key]["markets"].append(market)
            if not grouped_events[event_key]["title"]:
                grouped_events[event_key]["title"] = (
                    event_data.get("title")
                    or market.get("title")
                    or market.get("question", "")
                )

        for event in grouped_events.values():
            if len(event.get("markets", [])) >= 3:
                multi.append(event)
            if len(multi) >= limit:
                break

        return multi[:limit]

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
            token_id = self._extract_token_id(market)

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
