"""Tests for PolyTerm's real MCP server."""

import pytest

from polyterm.agent.contracts import envelope
from polyterm.agent.mcp import server as jsonl_server
from polyterm.agent.mcp.fastmcp_server import create_server
from polyterm.agent.mcp.server import handle_request


@pytest.mark.asyncio
async def test_fastmcp_server_lists_agent_tools():
    server = create_server()

    tools = await server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "agent.manifest" in tool_names
    assert "agent.schemas" in tool_names
    assert "agent.doctor" in tool_names
    assert "market.search" in tool_names
    assert "market.resolve" in tool_names
    assert "market.orderbook" in tool_names
    assert "market.price_history" in tool_names
    assert "market.research" in tool_names
    assert "market.explain_move" in tool_names
    assert "market.compare" in tool_names
    assert "scan.opportunities" in tool_names
    assert "archive.search" in tool_names
    assert "archive.status" in tool_names
    assert "archive.manifest" in tool_names
    assert "analytics.arbitrage" in tool_names
    assert "analytics.risk" in tool_names
    assert "analytics.thesis" in tool_names
    assert "wallet.inspect" in tool_names
    assert "wallet.whales" in tool_names
    assert "wallet.whale_trades" in tool_names
    assert "wallet.smart_money" in tool_names
    assert "agent.answer" in tool_names
    assert "alerts.create_price_rule" in tool_names
    assert "watch.scheduled_scan" in tool_names


@pytest.mark.asyncio
async def test_fastmcp_server_calls_existing_tool_handlers(monkeypatch):
    def fake_search(query, limit=10):
        return envelope(
            {"query": query, "count": 1, "markets": [{"question": "Test market"}]},
            meta={"tool": "market.search"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "market.search", fake_search)

    server = create_server()
    content, structured = await server.call_tool("market.search", {"query": "bitcoin", "limit": 1})
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["query"] == "bitcoin"
    assert result["data"]["count"] == 1
    assert result["meta"]["tool"] == "market.search"


@pytest.mark.asyncio
async def test_fastmcp_server_calls_market_research_handler(monkeypatch):
    def fake_research(market, prefetch_whales=False, min_notional=100000, hours=72, limit=5, persist=False):
        return envelope(
            {"query": market, "brief": {"headline": "Research ready"}, "quality_flags": ["research_brief"]},
            meta={"tool": "market.research"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "market.research", fake_research)

    server = create_server()
    content, structured = await server.call_tool(
        "market.research",
        {"market": "bitcoin", "prefetch_whales": True, "min_notional": 100000, "hours": 72, "limit": 5},
    )
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["query"] == "bitcoin"
    assert result["data"]["brief"]["headline"] == "Research ready"
    assert result["meta"]["tool"] == "market.research"


@pytest.mark.asyncio
async def test_fastmcp_server_calls_archive_search_handler(monkeypatch):
    def fake_archive_search(query="", limit=20):
        return envelope(
            {"query": query, "count": 1, "briefs": [{"id": 1, "query": query}]},
            meta={"tool": "archive.search"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "archive.search", fake_archive_search)

    server = create_server()
    content, structured = await server.call_tool("archive.search", {"query": "bitcoin", "limit": 5})
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["briefs"][0]["query"] == "bitcoin"
    assert result["meta"]["tool"] == "archive.search"


@pytest.mark.asyncio
async def test_fastmcp_server_calls_archive_status_handler(monkeypatch):
    def fake_archive_status(query="", market_id="", max_age_hours=24):
        return envelope(
            {"success": True, "query": query, "market_id": market_id, "freshness": {}, "quality_flags": ["archive_status"]},
            meta={"tool": "archive.status"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "archive.status", fake_archive_status)
    mcp = create_server()
    content, structured = await mcp.call_tool("archive.status", {"query": "bitcoin", "market_id": "m1", "max_age_hours": 12})
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["query"] == "bitcoin"
    assert result["meta"]["tool"] == "archive.status"


@pytest.mark.asyncio
async def test_fastmcp_server_calls_wallet_smart_money_handler(monkeypatch):
    def fake_smart_money(min_win_rate=0.70, min_trades=10, limit=20):
        return envelope(
            {"wallet_count": 1, "wallets": [{"address": "0xsharp"}], "min_win_rate": min_win_rate},
            meta={"tool": "wallet.smart_money"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "wallet.smart_money", fake_smart_money)
    mcp = create_server()
    content, structured = await mcp.call_tool("wallet.smart_money", {"min_win_rate": 0.8, "min_trades": 12, "limit": 5})
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["wallets"][0]["address"] == "0xsharp"
    assert result["meta"]["tool"] == "wallet.smart_money"


@pytest.mark.asyncio
async def test_fastmcp_server_calls_scan_opportunities_handler(monkeypatch):
    def fake_scan_opportunities(query="", limit=20, min_volume=1000, min_liquidity=0, max_archive_age_hours=24):
        return envelope(
            {"query": query, "limit": limit, "opportunities": [{"market_id": "m1"}]},
            meta={"tool": "scan.opportunities"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "scan.opportunities", fake_scan_opportunities)
    mcp = create_server()
    content, structured = await mcp.call_tool(
        "scan.opportunities",
        {"query": "bitcoin", "limit": 3, "min_volume": 5000, "min_liquidity": 1000, "max_archive_age_hours": 12},
    )
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["opportunities"][0]["market_id"] == "m1"
    assert result["meta"]["tool"] == "scan.opportunities"


@pytest.mark.asyncio
async def test_fastmcp_server_calls_agent_doctor_handler(monkeypatch):
    def fake_doctor(skip_network=False, check_mcp=True):
        return envelope(
            {"summary": {"status": "ok"}, "checks": [], "hermes_config": {}, "quality_flags": ["agent_doctor"]},
            meta={"tool": "agent.doctor"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "agent.doctor", fake_doctor)
    mcp = create_server()
    content, structured = await mcp.call_tool("agent.doctor", {"skip_network": True})
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["summary"]["status"] == "ok"
    assert result["meta"]["tool"] == "agent.doctor"


@pytest.mark.asyncio
async def test_fastmcp_server_returns_rich_agent_schema():
    server = create_server()

    content, structured = await server.call_tool("agent.schemas", {"tool": "wallet.whales"})
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["tool"] == "wallet.whales"
    assert "input_schema" in result["data"]
    assert "output_schema" in result["data"]
    assert result["meta"]["tool"] == "agent.schemas"


def test_legacy_jsonl_handler_still_available():
    result = handle_request({"method": "manifest"})

    assert result["success"] is True
    assert result["data"]["name"] == "polyterm"


@pytest.mark.asyncio
async def test_fastmcp_server_calls_wallet_whale_trades_handler(monkeypatch):
    def fake_whale_trades(limit=3, hours=48, min_notional=10000, sample_size=3000):
        return envelope(
            {"count": 1, "sample_size": sample_size, "trades": [{"wallet": "0xbig", "notional": 1325000}]},
            meta={"tool": "wallet.whale_trades"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "wallet.whale_trades", fake_whale_trades)
    mcp = create_server()
    content, structured = await mcp.call_tool(
        "wallet.whale_trades",
        {"limit": 3, "hours": 48, "min_notional": 10000, "sample_size": 3000},
    )
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["trades"][0]["notional"] == 1325000
    assert result["data"]["sample_size"] == 3000
    assert result["meta"]["tool"] == "wallet.whale_trades"


@pytest.mark.asyncio
async def test_fastmcp_server_calls_agent_answer_handler(monkeypatch):
    def fake_answer(query, hours=48, limit=3, min_notional=10000):
        return envelope(
            {"query": query, "intent": "whale_wagers", "confidence": "medium", "answer": "Top whale wagers ready."},
            meta={"tool": "agent.answer"},
        )

    monkeypatch.setitem(jsonl_server.TOOL_HANDLERS, "agent.answer", fake_answer)
    mcp = create_server()
    content, structured = await mcp.call_tool(
        "agent.answer",
        {"query": "3 biggest whale wagers last 48 hours", "hours": 48, "limit": 3},
    )
    result = structured["result"]

    assert content
    assert result["success"] is True
    assert result["data"]["intent"] == "whale_wagers"
    assert result["meta"]["tool"] == "agent.answer"
