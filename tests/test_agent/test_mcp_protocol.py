"""Standard MCP protocol server tests."""

import anyio
import pytest

pytest.importorskip("mcp.server.fastmcp")

from polyterm.agent.mcp import fastmcp_server
from polyterm.agent.mcp.server import TOOL_HANDLERS


def test_standard_mcp_registers_every_adapter_tool():
    async def check():
        server = fastmcp_server.create_server()
        tools = await server.list_tools()
        names = {tool.name for tool in tools}
        for name in TOOL_HANDLERS:
            assert name in names

    anyio.run(check)


def test_standard_mcp_tool_uses_existing_handler(monkeypatch):
    def fake_top_markets(limit=3, sort="volume24h"):
        return {
            "schema_version": "test",
            "success": True,
            "data": {"limit": limit, "sort": sort},
            "error": None,
            "meta": {"tool": "market.top"},
        }

    monkeypatch.setitem(fastmcp_server.TOOL_HANDLERS, "market.top", fake_top_markets)

    async def check():
        server = fastmcp_server.create_server()
        result = await server.call_tool("market.top", {"limit": 2, "sort": "liquidity"})
        payload = result[1]["result"]
        assert payload["success"] is True
        assert payload["data"] == {"limit": 2, "sort": "liquidity"}

    anyio.run(check)
