"""Tests for agent adapters exposing market.compare."""

from polyterm.agent import registry
from polyterm.agent.mcp import server
from polyterm.agent.mcp.tools import market


class FakeComparisonEngine:
    def compare(self, markets, hours=24):
        return {"query": markets, "hours": hours, "pairwise": [{"probability_gap": 0.2}]}


def test_market_compare_tool_wraps_core_result(monkeypatch):
    monkeypatch.setattr(market, "MarketComparisonEngine", lambda: FakeComparisonEngine())

    result = market.compare(["bitcoin-100k", "bitcoin-90k"], hours=12)

    assert result["success"] is True
    assert result["data"] == {"query": ["bitcoin-100k", "bitcoin-90k"], "hours": 12, "pairwise": [{"probability_gap": 0.2}]}
    assert result["meta"]["tool"] == "market.compare"


def test_jsonl_server_routes_market_compare(monkeypatch):
    monkeypatch.setattr(server.market, "compare", lambda markets, hours=24: {"success": True, "data": {"markets": markets, "hours": hours}, "error": None, "meta": {"tool": "market.compare"}, "schema_version": "2026-06-02"})
    monkeypatch.setitem(server.TOOL_HANDLERS, "market.compare", server.market.compare)

    result = server.handle_request({"tool": "market.compare", "args": {"markets": ["a", "b"], "hours": 6}})

    assert result["success"] is True
    assert result["data"] == {"markets": ["a", "b"], "hours": 6}
    assert result["meta"]["tool"] == "market.compare"


def test_manifest_declares_market_compare():
    tools = {tool["name"]: tool for tool in registry.get_manifest()["tools"]}

    assert "market.compare" in tools
    assert tools["market.compare"]["read_only"] is True
    assert tools["market.compare"]["args"] == {"markets": "array", "hours": "integer"}
