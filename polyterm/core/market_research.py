"""Flagship agent-native market research workflow."""

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from .trade_thesis import TradeThesisEngine
from ..db.database import Database
from ..db.models import MarketSnapshot

WhalePrefetcher = Callable[[str, float, int, int], Dict[str, Any]]


class MarketResearchEngine:
    """Compose PolyTerm tools into one agent-ready market research brief."""

    def __init__(
        self,
        thesis_engine: Optional[Any] = None,
        whale_prefetcher: Optional[WhalePrefetcher] = None,
        database: Optional[Database] = None,
    ):
        if thesis_engine is not None:
            self.thesis_engine = thesis_engine
        elif database is not None:
            self.thesis_engine = TradeThesisEngine(database=database)
        else:
            self.thesis_engine = TradeThesisEngine()
        self.whale_prefetcher = whale_prefetcher
        self.db = database or Database()

    def build(
        self,
        market: str,
        *,
        prefetch_whales: bool = False,
        min_notional: float = 100000,
        hours: int = 72,
        limit: int = 5,
        persist: bool = False,
    ) -> Dict[str, Any]:
        """Build a one-call market research brief for agents."""
        workflow = []

        if prefetch_whales:
            self.thesis_engine.build(market)
            prefetch_result = self._prefetch_whales(market, min_notional=min_notional, hours=hours, limit=limit)
            workflow.append(
                {
                    "tool": "wallet.whales",
                    "status": "completed" if prefetch_result.get("success", True) else "failed",
                    "args": {
                        "market": market,
                        "min_notional": min_notional,
                        "hours": hours,
                        "limit": limit,
                    },
                    "result": prefetch_result,
                }
            )

        thesis = self.thesis_engine.build(market)
        workflow.append({"tool": "analytics.thesis", "status": "completed", "args": {"market": market}})

        result = {
            "query": market,
            "market": thesis.get("market", {}),
            "brief": self._brief(thesis),
            "thesis": thesis,
            "quality_flags": self._quality_flags(thesis),
            "workflow": workflow,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        result["archive"] = self._archive_result(result, thesis=thesis, persist=persist)
        return result

    def _archive_result(self, payload: Dict[str, Any], *, thesis: Dict[str, Any], persist: bool) -> Dict[str, Any]:
        if not persist:
            return {"persisted": False, "brief_id": None, "captured_evidence": {}}
        brief_id = self.db.insert_research_brief(payload)
        captured = self._capture_evidence_snapshots(payload, thesis)
        return {"persisted": True, "brief_id": brief_id, "captured_evidence": captured}

    def _capture_evidence_snapshots(self, payload: Dict[str, Any], thesis: Dict[str, Any]) -> Dict[str, Any]:
        market = payload.get("market", {}) or {}
        market_id = str(market.get("gamma_market_id") or market.get("id") or "")
        market_slug = market.get("slug", "") or ""
        title = market.get("question") or market.get("title") or payload.get("query", "")
        token_ids = market.get("clob_token_ids") or []
        token_id = str(token_ids[0]) if token_ids else str((thesis.get("orderbook") or {}).get("token_id") or "")
        captured: Dict[str, Any] = {}

        captured["market_snapshot"] = self._capture_market_snapshot(market, market_id, market_slug, title, thesis)
        captured["orderbook_snapshot"] = self._capture_orderbook_snapshot(
            thesis.get("orderbook") or {}, market_id, market_slug, token_id
        )
        captured["price_history_snapshot"] = self._capture_price_history_snapshot(market_id, market_slug, token_id)
        return captured

    def _capture_market_snapshot(
        self,
        market: Dict[str, Any],
        market_id: str,
        market_slug: str,
        title: str,
        thesis: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not market_id:
            return {"persisted": False, "reason": "missing_market_id"}
        orderbook = thesis.get("orderbook") or {}
        snapshot = MarketSnapshot(
            market_id=market_id,
            market_slug=market_slug,
            title=title,
            probability=float(market.get("probability") or 0),
            volume_24h=float(market.get("volume_24h") or market.get("volume24hr") or market.get("volume") or 0),
            liquidity=float(market.get("liquidity") or 0),
            best_bid=float(orderbook.get("best_bid") or 0),
            best_ask=float(orderbook.get("best_ask") or 0),
            spread=float(orderbook.get("spread") or 0),
            timestamp=datetime.utcnow(),
        )
        return {"persisted": True, "snapshot_id": self.db.insert_snapshot(snapshot), "source": "market.research"}

    def _capture_orderbook_snapshot(
        self,
        orderbook: Dict[str, Any],
        market_id: str,
        market_slug: str,
        token_id: str,
    ) -> Dict[str, Any]:
        if not orderbook.get("available"):
            return {"persisted": False, "reason": orderbook.get("quality") or "orderbook_unavailable"}
        snapshot_id = self.db.insert_evidence_snapshot(
            "orderbook",
            orderbook,
            market_id=market_id,
            market_slug=market_slug,
            token_id=token_id,
            source="clob_orderbook",
        )
        return {"persisted": True, "snapshot_id": snapshot_id, "source": "clob_orderbook"}

    def _capture_price_history_snapshot(self, market_id: str, market_slug: str, token_id: str) -> Dict[str, Any]:
        if not token_id:
            return {"persisted": False, "reason": "missing_token_id"}
        clob = getattr(self.thesis_engine, "clob", None)
        if clob is None:
            return {"persisted": False, "reason": "missing_clob_client"}
        try:
            history = clob.get_price_history(token_id, interval="1h", fidelity=60)
        except Exception as exc:
            return {"persisted": False, "reason": str(exc)}
        snapshot_id = self.db.insert_evidence_snapshot(
            "price_history",
            {"token_id": token_id, "interval": "1h", "fidelity": 60, "history": history},
            market_id=market_id,
            market_slug=market_slug,
            token_id=token_id,
            source="clob_price_history",
        )
        return {
            "persisted": True,
            "snapshot_id": snapshot_id,
            "source": "clob_price_history",
            "point_count": len(history),
        }

    def _prefetch_whales(self, market: str, *, min_notional: float, hours: int, limit: int) -> Dict[str, Any]:
        if self.whale_prefetcher is not None:
            return self.whale_prefetcher(market, min_notional, hours, limit)

        from ..api.data_api import DataAPIClient
        from ..core.wallet_intelligence import WalletIntelligence
        from ..db.database import Database

        client = DataAPIClient()
        try:
            engine = WalletIntelligence(database=Database(), data_api=client)
            return engine.live_whales(min_notional=min_notional, hours=hours, limit=limit)
        finally:
            client.close()

    def _brief(self, thesis: Dict[str, Any]) -> Dict[str, Any]:
        thesis_body = thesis.get("thesis", {})
        flags = thesis.get("quality_flags", [])
        return {
            "headline": thesis_body.get("summary", "Market research brief generated."),
            "direction": thesis_body.get("direction", "neutral"),
            "confidence": thesis_body.get("confidence", 0),
            "recommendation": _recommendation(thesis_body.get("direction", "neutral"), thesis_body.get("confidence", 0)),
            "key_evidence": list(thesis_body.get("evidence", []))[:5],
            "key_risks": list(thesis_body.get("risks", []))[:5],
            "gaps": [flag for flag in flags if flag.endswith("_unavailable") or flag.startswith("missing_")],
            "next_actions": list(thesis_body.get("next_actions", []))[:5],
        }

    def _quality_flags(self, thesis: Dict[str, Any]) -> list[str]:
        flags = ["research_brief"]
        for flag in thesis.get("quality_flags", []):
            if flag not in flags:
                flags.append(flag)
        return flags


def _recommendation(direction: str, confidence: float) -> str:
    if confidence >= 0.6 and direction in {"yes", "no"}:
        return f"research_{direction}"
    return "research_neutral"
