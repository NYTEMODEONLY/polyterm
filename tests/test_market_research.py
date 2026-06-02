"""Tests for flagship market.research workflow."""

from polyterm.core.market_research import MarketResearchEngine


class FakeThesisEngine:
    def __init__(self):
        self.calls = []

    def build(self, market):
        self.calls.append(market)
        return {
            "market": {
                "input": market,
                "gamma_market_id": "2362221",
                "slug": "bitcoin-above-66k-on-june-2-2026",
                "condition_id": "condition-1",
                "clob_token_ids": ["token-yes", "token-no"],
                "title": "Bitcoin above $66K on June 2?",
                "probability": 0.72,
                "volume_24h": 250000,
                "liquidity": 500000,
            },
            "thesis": {
                "direction": "yes",
                "confidence": 0.65,
                "summary": "YES lean at 65% confidence.",
                "evidence": [
                    "YES probability is elevated at 72.00%.",
                    "CLOB spread is tight at 2.00%.",
                ],
                "risks": ["Limited local history; thesis relies mostly on live API snapshots."],
                "next_actions": ["Check order book depth before sizing."],
            },
            "evidence_sources": [
                {"id": "gamma_market", "status": "available", "metrics": {"probability": 0.72}, "records": []},
                {"id": "cached_whale_flow", "status": "unavailable", "metrics": {"trade_count": 0}, "records": []},
            ],
            "quality_flags": ["whale_flow_unavailable", "no_trade_execution"],
        }


def test_market_research_builds_agent_ready_brief_from_thesis():
    engine = MarketResearchEngine(thesis_engine=FakeThesisEngine())

    result = engine.build("bitcoin")

    assert result["query"] == "bitcoin"
    assert result["market"]["slug"] == "bitcoin-above-66k-on-june-2-2026"
    assert result["brief"]["headline"] == "YES lean at 65% confidence."
    assert result["brief"]["recommendation"] == "research_yes"
    assert result["brief"]["key_evidence"] == [
        "YES probability is elevated at 72.00%.",
        "CLOB spread is tight at 2.00%.",
    ]
    assert result["brief"]["gaps"] == ["whale_flow_unavailable"]
    assert result["thesis"]["quality_flags"] == ["whale_flow_unavailable", "no_trade_execution"]
    assert "research_brief" in result["quality_flags"]
    assert "whale_flow_unavailable" in result["quality_flags"]
    assert result["workflow"][0]["tool"] == "analytics.thesis"
    assert result["workflow"][0]["status"] == "completed"


def test_market_research_prefetches_whales_and_reruns_thesis():
    thesis_engine = FakeThesisEngine()
    calls = []

    def whale_prefetcher(market, min_notional, hours, limit):
        calls.append({"market": market, "min_notional": min_notional, "hours": hours, "limit": limit})
        return {"success": True, "source": "public_data_api", "cached_trade_count": 7}

    engine = MarketResearchEngine(thesis_engine=thesis_engine, whale_prefetcher=whale_prefetcher)

    result = engine.build("bitcoin", prefetch_whales=True, min_notional=100000, hours=72, limit=5)

    assert calls == [{"market": "bitcoin", "min_notional": 100000, "hours": 72, "limit": 5}]
    assert thesis_engine.calls == ["bitcoin", "bitcoin"]
    whale_step = result["workflow"][0]
    assert whale_step["tool"] == "wallet.whales"
    assert whale_step["status"] == "completed"
    assert whale_step["result"]["cached_trade_count"] == 7
    assert result["quality_flags"][0] == "research_brief"
