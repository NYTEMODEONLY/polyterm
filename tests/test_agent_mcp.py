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
