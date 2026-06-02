"""Tests for agent adapters exposing market.explain_move."""

from polyterm.agent.mcp import server
from polyterm.agent.mcp.tools import market


class FakeMoveExplainer:
    def explain(self, market, hours=24):
        return {"query": market, "move": {"hours": hours}}


def test_market_explain_move_tool_wraps_core_result(monkeypatch):
    monkeypatch.setattr(market, "MarketMoveExplainer", lambda: FakeMoveExplainer())

    result = market.explain_move("bitcoin", hours=12)

    assert result["success"] is True
    assert result["data"] == {"query": "bitcoin", "move": {"hours": 12}}
    assert result["meta"]["tool"] == "market.explain_move"


def test_jsonl_server_routes_market_explain_move(monkeypatch):
    monkeypatch.setattr(server.market, "explain_move", lambda market, hours=24: {"success": True, "data": {"market": market, "hours": hours}, "error": None, "meta": {"tool": "market.explain_move"}, "schema_version": "2026-06-02"})
    monkeypatch.setitem(server.TOOL_HANDLERS, "market.explain_move", server.market.explain_move)

    result = server.handle_request({"tool": "market.explain_move", "args": {"market": "bitcoin", "hours": 6}})

    assert result["success"] is True
    assert result["data"] == {"market": "bitcoin", "hours": 6}
    assert result["meta"]["tool"] == "market.explain_move"
