"""Gamma 24h volume heuristic. This is not whale identity or a trade feed."""

import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from ..api.gamma import GammaClient


EVIDENCE_LEVEL = "gamma_volume24hr_heuristic"
DISCLOSURE = (
    "Heuristic: markets with high Gamma 24h volume. This is not a whale trade, "
    "wallet address, or transaction. Use `polyterm whales --wallets` for "
    "wallet-level public Data API trades."
)


@dataclass
class HighVolumeMarket:
    """A market whose 24h volume exceeds a threshold."""

    market_id: str
    market_title: str
    volume_24hr: float
    last_price: float
    outcome_lean: str
    timestamp: int
    evidence_level: str = EVIDENCE_LEVEL

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_prices(raw: Any) -> List[Any]:
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
        return parsed if isinstance(parsed, list) else []
    if isinstance(raw, list):
        return raw
    return []


def _lean_from_yes_price(yes_price: float) -> str:
    if yes_price > 0.65:
        return "YES"
    if yes_price < 0.35:
        return "NO"
    return "MIXED"


def _extract_price_and_lean(market: Dict[str, Any]) -> tuple:
    last_price = float(market.get("lastTradePrice", 0) or 0)
    outcome = "Unknown"
    prices = _parse_prices(market.get("outcomePrices", []))
    if prices:
        try:
            yes_price = float(prices[0])
            outcome = _lean_from_yes_price(yes_price)
            if last_price == 0:
                last_price = yes_price
        except (TypeError, ValueError):
            pass

    if last_price == 0 or outcome == "Unknown":
        nested_markets = market.get("markets") or []
        if nested_markets:
            nested = nested_markets[0]
            if last_price == 0:
                last_price = float(nested.get("lastTradePrice", 0) or 0)
            nested_prices = _parse_prices(nested.get("outcomePrices", []))
            if nested_prices and outcome == "Unknown":
                try:
                    yes_price = float(nested_prices[0])
                    outcome = _lean_from_yes_price(yes_price)
                    if last_price == 0:
                        last_price = yes_price
                except (TypeError, ValueError):
                    pass
    return last_price, outcome


def detect_high_volume_markets(
    gamma_client: GammaClient,
    min_volume: float = 10000,
    limit: int = 50,
    now: Optional[int] = None,
) -> List[HighVolumeMarket]:
    """Return active markets whose 24h volume is at least ``min_volume``.

    This is market-level Gamma volume, not attributable whale trades.
    """
    markets = gamma_client.get_markets(limit=limit, active=True, closed=False) or []
    current_time = int(now if now is not None else time.time())
    results: List[HighVolumeMarket] = []

    for market in markets:
        market_id = market.get("id")
        if not market_id:
            continue
        volume_24hr = float(market.get("volume24hr", 0) or 0)
        if volume_24hr < min_volume:
            continue
        last_price, outcome = _extract_price_and_lean(market)
        results.append(
            HighVolumeMarket(
                market_id=str(market_id),
                market_title=str(market.get("title", market.get("question", "Unknown"))),
                volume_24hr=volume_24hr,
                last_price=last_price,
                outcome_lean=outcome,
                timestamp=current_time,
            )
        )

    return sorted(results, key=lambda item: item.volume_24hr, reverse=True)
