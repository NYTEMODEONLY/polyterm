"""Explain recent CLOB price moves for one market."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..api.clob import CLOBClient
from ..api.gamma import GammaClient
from ..api.market_utils import get_clob_token_ids, get_market_condition_id, market_probability_price


class MarketMoveExplainer:
    """Build a deterministic, read-only explanation for a recent YES price move."""

    def __init__(
        self,
        gamma_client: Optional[GammaClient] = None,
        clob_client: Optional[CLOBClient] = None,
    ):
        self.gamma = gamma_client or GammaClient()
        self.clob = clob_client or CLOBClient()

    def explain(self, market: str, hours: int = 24) -> Dict[str, Any]:
        """Explain the latest CLOB YES-price move for a market identifier."""
        market_data = self._resolve_market(market)
        token_ids = get_clob_token_ids(market_data)
        token_id = token_ids[0] if token_ids else ""
        history = self._price_history(token_id)
        orderbook = self._orderbook(token_id)
        move = _summarize_move(history, hours=hours)
        drivers = _drivers(move, orderbook)
        caveats = _caveats(move, token_id)

        return {
            "query": market,
            "market": {
                "input": market,
                "gamma_market_id": market_data.get("id"),
                "slug": market_data.get("slug"),
                "condition_id": get_market_condition_id(market_data),
                "clob_token_ids": token_ids,
                "title": market_data.get("question") or market_data.get("title") or market,
                "probability": market_probability_price(market_data),
                "volume_24h": market_data.get("volume24hr") or market_data.get("volume24Hr") or market_data.get("volume"),
                "liquidity": market_data.get("liquidity"),
            },
            "move": move,
            "headline": _headline(move),
            "drivers": drivers,
            "caveats": caveats,
            "orderbook": orderbook,
            "evidence_sources": _evidence_sources(market_data, token_id, history, orderbook),
            "quality_flags": _quality_flags(market_data, token_id, history, orderbook),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def _resolve_market(self, identifier: str) -> Dict[str, Any]:
        try:
            data = self.gamma.get_market(identifier)
            if data:
                return data
        except Exception:
            pass
        results = self.gamma.search_markets(identifier, limit=5)
        return _prefer_active_market(results)

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
            return {"available": False, "spread": None, "quality": "missing_token_id"}
        try:
            book = self.clob.get_order_book(token_id, depth=20)
            bids = book.get("bids") or []
            asks = book.get("asks") or []
            best_bid = float(bids[0].get("price", 0)) if bids else 0.0
            best_ask = float(asks[0].get("price", 0)) if asks else 0.0
            spread = best_ask - best_bid if best_ask and best_bid else None
            return {
                "available": True,
                "token_id": token_id,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "bid_levels": len(bids),
                "ask_levels": len(asks),
            }
        except Exception as exc:
            return {"available": False, "token_id": token_id, "spread": None, "quality": str(exc)}


def _summarize_move(history: List[Dict[str, Any]], hours: int) -> Dict[str, Any]:
    prices = [_extract_price(point) for point in history]
    prices = [price for price in prices if price is not None]
    if len(prices) < 2:
        return {
            "direction": "unknown",
            "start_price": None,
            "end_price": None,
            "absolute_change": None,
            "relative_change": None,
            "hours": hours,
            "points": len(prices),
        }

    start_price = prices[0]
    end_price = prices[-1]
    absolute_change = round(end_price - start_price, 4)
    relative_change = round(absolute_change / start_price, 4) if start_price else None
    direction = "up" if absolute_change > 0.005 else "down" if absolute_change < -0.005 else "flat"
    return {
        "direction": direction,
        "start_price": round(start_price, 4),
        "end_price": round(end_price, 4),
        "absolute_change": absolute_change,
        "relative_change": relative_change,
        "hours": hours,
        "points": len(prices),
    }


def _extract_price(point: Dict[str, Any]) -> Optional[float]:
    for key in ("p", "price", "value"):
        if key not in point:
            continue
        try:
            return float(point[key])
        except (TypeError, ValueError):
            continue
    return None


def _headline(move: Dict[str, Any]) -> str:
    if move["direction"] == "unknown":
        return "Recent YES move is unavailable."
    points = abs(float(move.get("absolute_change") or 0)) * 100
    return f"YES moved {move['direction']} {points:.1f} points over {move['hours']}h."


def _drivers(move: Dict[str, Any], orderbook: Dict[str, Any]) -> List[str]:
    drivers: List[str] = []
    if move["direction"] != "unknown":
        drivers.append(
            "Price history shows a "
            f"{abs(float(move['absolute_change'])) * 100:.1f} point YES move "
            f"from {float(move['start_price']):.1%} to {float(move['end_price']):.1%}."
        )
    spread = orderbook.get("spread")
    if spread is not None:
        drivers.append(
            "Current order book spread is "
            f"{float(spread) * 100:.1f} points, so the move is backed by a tradable CLOB quote."
        )
    return drivers


def _caveats(move: Dict[str, Any], token_id: str) -> List[str]:
    caveats = ["PolyTerm is no-custody and does not place trades."]
    if not token_id:
        caveats.insert(0, "Missing CLOB token ID; cannot fetch price history.")
    elif move["direction"] == "unknown":
        caveats.insert(0, "Price history unavailable; cannot attribute a recent move.")
    return caveats


def _evidence_sources(
    market_data: Dict[str, Any],
    token_id: str,
    history: List[Dict[str, Any]],
    orderbook: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [
        {
            "id": "gamma_market",
            "source": "gamma_api",
            "status": "available" if market_data else "unavailable",
            "records": [{"id": market_data.get("id"), "slug": market_data.get("slug")} ] if market_data else [],
        },
        {
            "id": "clob_price_history",
            "source": "clob_api",
            "status": "available" if history else "unavailable",
            "metrics": {"points": len(history), "token_id": token_id},
            "records": history[:5],
        },
        {
            "id": "clob_orderbook",
            "source": "clob_api",
            "status": "available" if orderbook.get("available") else "unavailable",
            "metrics": {"spread": orderbook.get("spread"), "best_bid": orderbook.get("best_bid"), "best_ask": orderbook.get("best_ask")},
            "records": [{"token_id": token_id}],
        },
    ]


def _quality_flags(
    market_data: Dict[str, Any],
    token_id: str,
    history: List[Dict[str, Any]],
    orderbook: Dict[str, Any],
) -> List[str]:
    flags = []
    if not market_data:
        flags.append("market_not_found")
    if not token_id:
        flags.append("missing_clob_token_id")
    flags.append("price_history_available" if history else "price_history_unavailable")
    flags.append("orderbook_available" if orderbook.get("available") else "orderbook_unavailable")
    flags.append("no_trade_execution")
    return flags


def _prefer_active_market(markets: list) -> Dict[str, Any]:
    for market in markets:
        if _is_current_market(market):
            return market
    return markets[0] if markets else {}


def _is_current_market(market: Dict[str, Any]) -> bool:
    if not market.get("active", True) or market.get("closed", False):
        return False
    end_date = market.get("endDate") or market.get("end_date_iso")
    if not end_date:
        return True
    try:
        parsed = datetime.fromisoformat(str(end_date).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed > datetime.now(timezone.utc)
    except Exception:
        return True
