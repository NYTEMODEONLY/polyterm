"""Agent-native market comparison and divergence summaries."""

from datetime import datetime
from itertools import combinations
from typing import Any, Dict, List, Optional

from ..api.clob import CLOBClient
from ..api.gamma import GammaClient
from ..api.market_utils import get_clob_token_ids, get_market_condition_id, market_probability_price
from .market_move import _prefer_active_market, _summarize_move


class MarketComparisonEngine:
    """Compare two or more resolved markets with price, liquidity, and move context."""

    def __init__(
        self,
        gamma_client: Optional[GammaClient] = None,
        clob_client: Optional[CLOBClient] = None,
    ):
        self.gamma = gamma_client or GammaClient()
        self.clob = clob_client or CLOBClient()

    def compare(self, markets: List[str], hours: int = 24) -> Dict[str, Any]:
        """Return a stable JSON-ready comparison for market identifiers."""
        resolved = [self._market_summary(identifier, hours=hours) for identifier in markets]
        pairwise = _pairwise_differences(resolved)
        quality_flags = _quality_flags(resolved, pairwise)

        return {
            "query": list(markets),
            "count": len(resolved),
            "hours": hours,
            "markets": resolved,
            "pairwise": pairwise,
            "headline": _headline(resolved, pairwise),
            "divergence_summary": _divergence_summary(pairwise),
            "evidence_sources": _evidence_sources(resolved),
            "quality_flags": quality_flags,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def _resolve_market(self, identifier: str) -> Dict[str, Any]:
        try:
            market = self.gamma.get_market(identifier)
            if market:
                return market
        except Exception:
            pass
        try:
            return _prefer_active_market(self.gamma.search_markets(identifier, limit=5))
        except Exception:
            return {}

    def _market_summary(self, identifier: str, hours: int) -> Dict[str, Any]:
        market = self._resolve_market(identifier)
        token_ids = get_clob_token_ids(market)
        token_id = token_ids[0] if token_ids else ""
        history = self._price_history(token_id)
        orderbook = self._orderbook(token_id)

        return {
            "input": identifier,
            "gamma_market_id": market.get("id"),
            "slug": market.get("slug"),
            "condition_id": get_market_condition_id(market),
            "clob_token_ids": token_ids,
            "title": market.get("question") or market.get("title") or identifier,
            "probability": market_probability_price(market),
            "volume": _as_float(market.get("volume")),
            "volume_24h": _as_float(market.get("volume24hr") or market.get("volume24Hr")),
            "liquidity": _as_float(market.get("liquidity")),
            "move": _summarize_move(history, hours=hours),
            "orderbook": orderbook,
            "history_points": len(history),
        }

    def _price_history(self, token_id: str) -> List[Dict[str, Any]]:
        if not token_id:
            return []
        try:
            history = self.clob.get_price_history(token_id, interval="1h", fidelity=60)
        except Exception:
            return []
        return history if isinstance(history, list) else []

    def _orderbook(self, token_id: str) -> Dict[str, Any]:
        if not token_id:
            return {"available": False, "spread": None}
        try:
            book = self.clob.get_order_book(token_id, depth=20)
            bids = book.get("bids") or []
            asks = book.get("asks") or []
            best_bid = _as_float(bids[0].get("price")) if bids else None
            best_ask = _as_float(asks[0].get("price")) if asks else None
            spread = round(best_ask - best_bid, 4) if best_bid is not None and best_ask is not None else None
            return {"available": True, "best_bid": best_bid, "best_ask": best_ask, "spread": spread}
        except Exception as exc:
            return {"available": False, "spread": None, "quality": str(exc)}


def _pairwise_differences(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pairs = []
    for left, right in combinations(markets, 2):
        left_probability = _as_float(left.get("probability")) or 0.0
        right_probability = _as_float(right.get("probability")) or 0.0
        pairs.append(
            {
                "left_slug": left.get("slug"),
                "right_slug": right.get("slug"),
                "probability_gap": round(abs(left_probability - right_probability), 4),
                "liquidity_gap": round(abs((_as_float(left.get("liquidity")) or 0.0) - (_as_float(right.get("liquidity")) or 0.0)), 2),
                "volume_gap": round(abs((_as_float(left.get("volume")) or 0.0) - (_as_float(right.get("volume")) or 0.0)), 2),
                "combined_probability": round(left_probability + right_probability, 4),
            }
        )
    return pairs


def _headline(markets: List[Dict[str, Any]], pairwise: List[Dict[str, Any]]) -> str:
    if len(markets) < 2:
        return "Need at least two markets for comparison."
    widest = max((pair["probability_gap"] for pair in pairwise), default=0.0)
    return f"Compared {len(markets)} markets; widest YES gap is {widest * 100:.1f} points."


def _divergence_summary(pairwise: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not pairwise:
        return {"widest_probability_gap": None, "notable_pairs": []}
    widest = max(pairwise, key=lambda pair: pair["probability_gap"])
    notable = [pair for pair in pairwise if pair["probability_gap"] >= 0.1]
    return {"widest_probability_gap": widest, "notable_pairs": notable}


def _evidence_sources(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": "gamma_markets",
            "source": "gamma_api",
            "status": "available" if markets else "unavailable",
            "records": [{"id": market.get("gamma_market_id"), "slug": market.get("slug")} for market in markets],
        },
        {
            "id": "clob_price_history",
            "source": "clob_api",
            "status": "available" if any(market.get("history_points", 0) for market in markets) else "unavailable",
            "metrics": {"markets_with_history": sum(1 for market in markets if market.get("history_points", 0))},
        },
        {
            "id": "clob_orderbooks",
            "source": "clob_api",
            "status": "available" if any(market.get("orderbook", {}).get("available") for market in markets) else "unavailable",
        },
    ]


def _quality_flags(markets: List[Dict[str, Any]], pairwise: List[Dict[str, Any]]) -> List[str]:
    flags = ["no_trade_execution"]
    if len(markets) < 2:
        flags.append("need_at_least_two_markets")
    if pairwise:
        flags.append("pairwise_comparison_available")
    flags.append("price_history_available" if any(market.get("history_points", 0) for market in markets) else "price_history_unavailable")
    flags.append("orderbook_available" if any(market.get("orderbook", {}).get("available") for market in markets) else "orderbook_unavailable")
    return flags


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
