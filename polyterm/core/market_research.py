"""Flagship agent-native market research workflow."""

from typing import Any, Callable, Dict, Optional

from .trade_thesis import TradeThesisEngine

WhalePrefetcher = Callable[[str, float, int, int], Dict[str, Any]]


class MarketResearchEngine:
    """Compose PolyTerm tools into one agent-ready market research brief."""

    def __init__(self, thesis_engine: Optional[Any] = None, whale_prefetcher: Optional[WhalePrefetcher] = None):
        self.thesis_engine = thesis_engine or TradeThesisEngine()
        self.whale_prefetcher = whale_prefetcher

    def build(
        self,
        market: str,
        *,
        prefetch_whales: bool = False,
        min_notional: float = 100000,
        hours: int = 72,
        limit: int = 5,
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

        return {
            "query": market,
            "market": thesis.get("market", {}),
            "brief": self._brief(thesis),
            "thesis": thesis,
            "quality_flags": self._quality_flags(thesis),
            "workflow": workflow,
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
