"""Cross-venue hedge and arbitrage monitoring."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from ..api.gamma import GammaClient
from ..api.market_utils import market_probability_price


@dataclass
class VenueMarket:
    """Normalized market from an external venue."""

    venue: str
    id: str
    title: str
    yes_price: float
    url: str = ""
    stale: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "venue": self.venue,
            "id": self.id,
            "title": self.title,
            "yes_price": self.yes_price,
            "url": self.url,
            "stale": self.stale,
        }


class CrossVenueMonitor:
    """Read-only monitor for cross-venue spreads."""

    def __init__(self, gamma_client: Optional[GammaClient] = None, kalshi_base_url: str = "https://api.elections.kalshi.com/trade-api/v2"):
        self.gamma = gamma_client or GammaClient()
        self.kalshi_base_url = kalshi_base_url.rstrip("/")

    def scan(
        self,
        query: str,
        min_spread: float = 0.025,
        venues: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Scan Polymarket against supported external venues."""
        venues = venues or ["polymarket", "kalshi"]
        polymarket = self._polymarket_markets(query=query, limit=limit)
        external = []
        if "kalshi" in venues:
            external.extend(self._kalshi_markets(query=query, limit=limit))

        opportunities = []
        for poly in polymarket:
            for other in external:
                confidence = self._match_confidence(poly.title, other.title)
                if confidence < 0.45:
                    continue
                spread = abs(poly.yes_price - other.yes_price)
                if spread >= min_spread:
                    opportunities.append({
                        "polymarket": poly.to_dict(),
                        "other": other.to_dict(),
                        "spread": spread,
                        "spread_pct": spread * 100,
                        "match_confidence": round(confidence, 2),
                        "fee_adjusted_spread": max(spread - 0.02, 0),
                        "quality_flags": self._quality_flags(other, confidence),
                    })
        opportunities.sort(key=lambda row: (row["fee_adjusted_spread"], row["match_confidence"]), reverse=True)
        return {
            "query": query,
            "venues": venues,
            "count": len(opportunities),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "opportunities": opportunities,
        }

    def _polymarket_markets(self, query: str, limit: int) -> List[VenueMarket]:
        markets = self.gamma.search_markets(query, limit=limit) if query else self.gamma.get_markets(limit=limit)
        normalized = []
        for market in markets:
            normalized.append(VenueMarket(
                venue="polymarket",
                id=str(market.get("id") or market.get("conditionId") or ""),
                title=market.get("question") or market.get("title") or "",
                yes_price=market_probability_price(market),
                url=f"https://polymarket.com/event/{market.get('slug', '')}" if market.get("slug") else "",
            ))
        return normalized

    def _kalshi_markets(self, query: str, limit: int) -> List[VenueMarket]:
        try:
            response = requests.get(
                f"{self.kalshi_base_url}/markets",
                params={"limit": limit, "search": query} if query else {"limit": limit},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            rows = data.get("markets", data if isinstance(data, list) else [])
        except Exception:
            return []

        markets = []
        for row in rows[:limit]:
            yes_price = row.get("yes_ask") or row.get("yes_bid") or row.get("last_price") or 0
            if yes_price and yes_price > 1:
                yes_price = float(yes_price) / 100.0
            markets.append(VenueMarket(
                venue="kalshi",
                id=str(row.get("ticker") or row.get("id") or ""),
                title=row.get("title") or row.get("subtitle") or row.get("event_ticker") or "",
                yes_price=float(yes_price or 0),
                url=row.get("url") or "",
            ))
        return markets

    def _match_confidence(self, left: str, right: str) -> float:
        left_words = {word for word in left.lower().replace("?", "").split() if len(word) > 3}
        right_words = {word for word in right.lower().replace("?", "").split() if len(word) > 3}
        if not left_words or not right_words:
            return 0.0
        return len(left_words & right_words) / len(left_words | right_words)

    def _quality_flags(self, market: VenueMarket, confidence: float) -> List[str]:
        flags = []
        if confidence < 0.65:
            flags.append("manual_review_match")
        if market.stale:
            flags.append("stale_external_data")
        flags.append("fee_estimate_only")
        return flags
