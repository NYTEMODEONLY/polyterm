"""Explainable market-level trade thesis generation."""

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..api.clob import CLOBClient
from ..api.gamma import GammaClient
from ..api.market_utils import get_clob_token_ids, get_market_condition_id, market_probability_price
from ..db.database import Database
from .risk_score import MarketRiskScorer


class TradeThesisEngine:
    """Compose PolyTerm signals into one explainable market thesis."""

    def __init__(
        self,
        gamma_client: Optional[GammaClient] = None,
        clob_client: Optional[CLOBClient] = None,
        database: Optional[Database] = None,
    ):
        self.gamma = gamma_client or GammaClient()
        self.clob = clob_client or CLOBClient()
        self.db = database or Database()

    def build(self, market: str) -> Dict[str, Any]:
        """Build a read-only trade thesis for a market identifier."""
        market_data = self._resolve_market(market)
        title = market_data.get("question") or market_data.get("title") or market
        condition_id = get_market_condition_id(market_data)
        token_ids = get_clob_token_ids(market_data)
        probability = market_probability_price(market_data)
        orderbook = self._orderbook(token_ids[0] if token_ids else "")
        risk = self._risk(market_data)
        local_history = self._local_history(market_data.get("id") or condition_id or market)
        whale_flow = self._whale_flow(market_data, hours=72, min_notional=10000)

        signal_direction = "neutral"
        evidence = []
        risks = []

        if probability >= 0.65:
            signal_direction = "yes"
            evidence.append(f"YES probability is elevated at {probability:.2%}.")
        elif probability <= 0.35 and probability > 0:
            signal_direction = "no"
            evidence.append(f"YES probability is low at {probability:.2%}.")
        else:
            evidence.append(f"Market is near balanced at {probability:.2%}.")

        if orderbook.get("spread") is not None:
            spread = float(orderbook.get("spread") or 0)
            if spread <= 0.03:
                evidence.append(f"CLOB spread is tight at {spread:.2%}.")
            else:
                risks.append(f"CLOB spread is wide at {spread:.2%}.")

        if risk.get("overall_grade") in {"D", "F"}:
            risks.append(f"Risk grade is {risk.get('overall_grade')}.")
        elif risk.get("overall_grade"):
            evidence.append(f"Risk grade is {risk.get('overall_grade')}.")

        if local_history.get("data_points", 0) >= 3:
            evidence.append(f"Local archive has {local_history['data_points']} recent data points.")
        else:
            risks.append("Limited local history; thesis relies mostly on live API snapshots.")

        if whale_flow.get("trade_count", 0):
            evidence.append(
                "Cached whale flow shows "
                f"{whale_flow['trade_count']} large trade(s) from {whale_flow['wallet_count']} wallet(s) "
                f"totaling ${whale_flow['total_notional']:,.0f}; top outcome: {whale_flow.get('top_outcome') or 'unknown'}."
            )
        else:
            risks.append("No cached whale flow for this market; run wallet.whales to enrich local evidence.")

        confidence = self._confidence(probability, orderbook, risk, local_history)

        return {
            "market": {
                "input": market,
                "gamma_market_id": market_data.get("id"),
                "slug": market_data.get("slug"),
                "condition_id": condition_id,
                "clob_token_ids": token_ids,
                "title": title,
                "probability": probability,
                "volume_24h": market_data.get("volume24hr") or market_data.get("volume24Hr") or market_data.get("volume"),
                "liquidity": market_data.get("liquidity"),
                "end_date": market_data.get("endDate"),
            },
            "thesis": {
                "direction": signal_direction,
                "confidence": confidence,
                "summary": self._summary(signal_direction, confidence, risks),
                "evidence": evidence,
                "risks": risks,
                "next_actions": [
                    "Check order book depth before sizing.",
                    "Compare thesis with recent wallet activity.",
                    "Use quicktrade link for execution; PolyTerm remains no-custody.",
                ],
            },
            "orderbook": orderbook,
            "risk": risk,
            "local_history": local_history,
            "whale_flow": whale_flow,
            "quality_flags": self._quality_flags(market_data, token_ids, orderbook, whale_flow),
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

    def _risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        scorer = MarketRiskScorer()
        assessment = scorer.score_market(
            market_id=str(market_data.get("id") or get_market_condition_id(market_data) or ""),
            title=market_data.get("question") or market_data.get("title") or "",
            description=market_data.get("description") or "",
            end_date=None,
            volume_24h=float(market_data.get("volume24hr") or market_data.get("volume") or 0),
            liquidity=float(market_data.get("liquidity") or 0),
            spread=float(market_data.get("spread") or 0),
            category=market_data.get("category") or "",
            resolution_source=market_data.get("resolutionSource") or "",
        )
        return assessment.to_dict()

    def _local_history(self, market_id: str) -> Dict[str, Any]:
        history = self.db.get_market_history(market_id, hours=72, limit=500) if market_id else []
        return {
            "data_points": len(history),
            "latest_probability": history[0].probability if history else None,
            "oldest_probability": history[-1].probability if history else None,
        }

    def _whale_flow(self, market_data: Dict[str, Any], hours: int = 72, min_notional: float = 10000) -> Dict[str, Any]:
        """Summarize cached large trades for the resolved market."""
        identifiers = _market_identifiers(market_data)
        if not identifiers:
            return {
                "source": "local_cache",
                "hours": hours,
                "min_notional": min_notional,
                "trade_count": 0,
                "wallet_count": 0,
                "total_notional": 0.0,
                "top_outcome": None,
                "trades": [],
            }

        try:
            large_trades = self.db.get_large_trades(min_notional=min_notional, hours=hours)
        except Exception:
            large_trades = []

        matched = [trade for trade in large_trades if _trade_matches_market(trade, identifiers)]
        matched.sort(key=lambda trade: (trade.notional, trade.timestamp), reverse=True)
        outcomes = Counter(trade.outcome for trade in matched if trade.outcome)
        wallets = {trade.wallet_address for trade in matched if trade.wallet_address}

        return {
            "source": "local_cache",
            "hours": hours,
            "min_notional": min_notional,
            "trade_count": len(matched),
            "wallet_count": len(wallets),
            "total_notional": sum(trade.notional for trade in matched),
            "top_outcome": outcomes.most_common(1)[0][0] if outcomes else None,
            "trades": [trade.to_dict() for trade in matched[:5]],
        }

    def _confidence(self, probability: float, orderbook: Dict[str, Any], risk: Dict[str, Any], local_history: Dict[str, Any]) -> float:
        score = 0.35
        if probability and (probability >= 0.65 or probability <= 0.35):
            score += 0.15
        if orderbook.get("available"):
            score += 0.15
        if risk.get("overall_grade") in {"A", "B", "C"}:
            score += 0.15
        if local_history.get("data_points", 0) >= 3:
            score += 0.10
        return round(min(score, 0.95), 2)

    def _summary(self, direction: str, confidence: float, risks: list) -> str:
        risk_note = " with notable caveats" if risks else ""
        return f"{direction.upper()} lean at {confidence:.0%} confidence{risk_note}."

    def _quality_flags(
        self,
        market_data: Dict[str, Any],
        token_ids: list,
        orderbook: Dict[str, Any],
        whale_flow: Dict[str, Any],
    ) -> list:
        flags = []
        if not market_data:
            flags.append("market_not_found")
        if not token_ids:
            flags.append("missing_clob_token_ids")
        if not orderbook.get("available"):
            flags.append("orderbook_unavailable")
        if whale_flow.get("trade_count", 0):
            flags.append("cached_whale_flow")
        else:
            flags.append("whale_flow_unavailable")
        flags.append("no_trade_execution")
        return flags


def _market_identifiers(market_data: Dict[str, Any]) -> set[str]:
    """Return every local-cache identifier that can refer to a resolved market."""
    identifiers = {
        str(market_data.get("id") or ""),
        str(market_data.get("slug") or ""),
        str(get_market_condition_id(market_data) or ""),
    }
    for token_id in get_clob_token_ids(market_data):
        identifiers.add(str(token_id))
    return {identifier for identifier in identifiers if identifier}


def _trade_matches_market(trade: Any, identifiers: set[str]) -> bool:
    """Return whether a cached trade belongs to the resolved market."""
    return any(
        str(value or "") in identifiers
        for value in (
            getattr(trade, "market_id", ""),
            getattr(trade, "market_slug", ""),
        )
    )


def _prefer_active_market(markets: list) -> Dict[str, Any]:
    """Prefer active, non-closed search results."""
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
