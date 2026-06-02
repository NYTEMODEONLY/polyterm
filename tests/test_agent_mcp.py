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
    assert "market.search" in tool_names
    assert "market.resolve" in tool_names
    assert "market.research" in tool_names
    assert "archive.search" in tool_names
    assert "archive.status" in tool_names
    assert "analytics.thesis" in tool_names
    assert "wallet.inspect" in tool_names


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
