"""FastMCP server for PolyTerm agent tools.

This module exposes the existing agent-safe callable tools through the real MCP
stdio protocol. The older JSON-lines adapter remains available in
``polyterm.agent.mcp.server`` for lightweight integrations that do not speak MCP.
"""

from typing import Any, Dict, Optional

from ..contracts import envelope, error_envelope
from ..registry import get_manifest
from ..schemas import all_schemas, schema_for_tool
from .server import TOOL_HANDLERS

try:  # pragma: no cover - exercised by CLI/integration tests when installed
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None  # type: ignore[assignment]


SERVER_NAME = "polyterm"


def _call_tool(tool_name: str, **kwargs: Any) -> Dict[str, Any]:
    """Call an agent tool and keep MCP responses in PolyTerm's envelope."""
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return error_envelope(f"Unknown tool: {tool_name}", meta={"tool": tool_name})

    try:
        return handler(**kwargs)
    except Exception as exc:
        return error_envelope(str(exc), meta={"tool": tool_name})


def create_server() -> Any:
    """Create the FastMCP application for PolyTerm."""
    if FastMCP is None:
        raise RuntimeError("The 'mcp' package is required. Install with: pip install mcp")

    mcp = FastMCP(
        SERVER_NAME,
        instructions=(
            "PolyTerm exposes no-custody Polymarket intelligence tools. "
            "Tools return PolyTerm's stable JSON envelope with success, data, "
            "error, and meta fields."
        ),
    )

    @mcp.tool(
        name="agent.manifest",
        description="Return PolyTerm's machine-readable agent tool manifest and safety flags.",
    )
    def agent_manifest() -> Dict[str, Any]:
        return envelope(get_manifest(), meta={"tool": "agent.manifest"})

    @mcp.tool(
        name="agent.schemas",
        description="Return rich input/output schemas for one PolyTerm tool or every agent tool.",
    )
    def agent_schemas(tool: str = "") -> Dict[str, Any]:
        try:
            data = schema_for_tool(tool) if tool else all_schemas()
            return envelope(data, meta={"tool": "agent.schemas"})
        except KeyError as exc:
            return error_envelope(str(exc), meta={"tool": "agent.schemas"})

    @mcp.tool(name="market.search", description="Search active Polymarket markets by query.")
    def market_search(query: str, limit: int = 10) -> Dict[str, Any]:
        return _call_tool("market.search", query=query, limit=limit)

    @mcp.tool(
        name="market.resolve",
        description="Resolve a slug, URL, Gamma ID, condition ID, or token ID into market identifiers.",
    )
    def market_resolve(identifier: str) -> Dict[str, Any]:
        return _call_tool("market.resolve", identifier=identifier)

    @mcp.tool(
        name="market.research",
        description="Generate a flagship one-call market research brief with thesis, evidence, gaps, and workflow.",
    )
    def market_research(
        market: str,
        prefetch_whales: bool = False,
        min_notional: float = 100000,
        hours: int = 72,
        limit: int = 5,
        persist: bool = False,
    ) -> Dict[str, Any]:
        return _call_tool(
            "market.research",
            market=market,
            prefetch_whales=prefetch_whales,
            min_notional=min_notional,
            hours=hours,
            limit=limit,
            persist=persist,
        )

    @mcp.tool(
        name="market.explain_move",
        description="Explain a recent YES price move with CLOB price history, order book context, and quality flags.",
    )
    def market_explain_move(market: str, hours: int = 24) -> Dict[str, Any]:
        return _call_tool("market.explain_move", market=market, hours=hours)

    @mcp.tool(
        name="analytics.arbitrage",
        description="Scan Polymarket and optional venues for arbitrage opportunities.",
    )
    def analytics_arbitrage(min_spread: float = 0.025, venues: str = "polymarket") -> Dict[str, Any]:
        return _call_tool("analytics.arbitrage", min_spread=min_spread, venues=venues)

    @mcp.tool(
        name="analytics.thesis",
        description="Generate an explainable market-level trade thesis.",
    )
    def analytics_thesis(market: str) -> Dict[str, Any]:
        return _call_tool("analytics.thesis", market=market)

    @mcp.tool(
        name="archive.search",
        description="Search locally archived PolyTerm research briefs.",
    )
    def archive_search(query: str = "", limit: int = 20) -> Dict[str, Any]:
        return _call_tool("archive.search", query=query, limit=limit)

    @mcp.tool(
        name="archive.status",
        description="Report local archive coverage, freshness, and recommended refresh actions.",
    )
    def archive_status(query: str = "", market_id: str = "", max_age_hours: int = 24) -> Dict[str, Any]:
        return _call_tool("archive.status", query=query, market_id=market_id, max_age_hours=max_age_hours)

    @mcp.tool(
        name="wallet.inspect",
        description="Inspect a wallet using public Data API and local PolyTerm evidence.",
    )
    def wallet_inspect(address: str, limit: int = 100) -> Dict[str, Any]:
        return _call_tool("wallet.inspect", address=address, limit=limit)

    @mcp.tool(
        name="wallet.whales",
        description="Return wallet-level whale activity and smart-money candidates.",
    )
    def wallet_whales(min_notional: float = 10000, hours: int = 24, limit: int = 20) -> Dict[str, Any]:
        return _call_tool("wallet.whales", min_notional=min_notional, hours=hours, limit=limit)

    return mcp


def main(transport: str = "stdio", mount_path: Optional[str] = None) -> int:
    """Run PolyTerm's FastMCP server."""
    server = create_server()
    server.run(transport=transport, mount_path=mount_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
