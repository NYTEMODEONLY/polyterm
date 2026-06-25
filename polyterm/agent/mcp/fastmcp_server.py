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

    @mcp.tool(
        name="agent.doctor",
        description="Diagnose PolyTerm agent installation, schemas, manifests, MCP boot, APIs, and archive health.",
    )
    def agent_doctor(skip_network: bool = True) -> Dict[str, Any]:
        return _call_tool("agent.doctor", skip_network=skip_network, check_mcp=False)

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
        name="market.top",
        description="Return top active Polymarket markets from live Gamma market data.",
    )
    def market_top(limit: int = 3, sort: str = "volume24h") -> Dict[str, Any]:
        return _call_tool("market.top", limit=limit, sort=sort)

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

    @mcp.tool(name="market.orderbook", description="Return order book and spread analysis for a CLOB token ID.")
    def market_orderbook(token_id: str, depth: int = 20) -> Dict[str, Any]:
        return _call_tool("market.orderbook", token_id=token_id, depth=depth)

    @mcp.tool(name="market.price_history", description="Return CLOB-backed price history for a market.")
    def market_price_history(market: str, hours: int = 24) -> Dict[str, Any]:
        return _call_tool("market.price_history", market=market, hours=hours)

    @mcp.tool(
        name="market.movers",
        description="Return active markets that flipped or had large available price changes.",
    )
    def market_movers(limit: int = 3, hours: int = 48, min_abs_change: float = 0.05) -> Dict[str, Any]:
        return _call_tool(
            "market.movers",
            limit=limit,
            hours=hours,
            min_abs_change=min_abs_change,
        )

    @mcp.tool(
        name="market.explain_move",
        description="Explain a recent YES price move with CLOB price history, order book context, and quality flags.",
    )
    def market_explain_move(market: str, hours: int = 24) -> Dict[str, Any]:
        return _call_tool("market.explain_move", market=market, hours=hours)

    @mcp.tool(
        name="market.compare",
        description="Compare markets side by side with YES price gaps, recent moves, liquidity, and evidence quality flags.",
    )
    def market_compare(markets: list[str], hours: int = 24) -> Dict[str, Any]:
        return _call_tool("market.compare", markets=markets, hours=hours)

    @mcp.tool(
        name="scan.opportunities",
        description="Scan active markets for unusual moves, stale archive coverage, and research-worthy opportunities.",
    )
    def scan_opportunities(
        query: str = "",
        limit: int = 20,
        min_volume: float = 1000,
        min_liquidity: float = 0,
        max_archive_age_hours: int = 24,
    ) -> Dict[str, Any]:
        return _call_tool(
            "scan.opportunities",
            query=query,
            limit=limit,
            min_volume=min_volume,
            min_liquidity=min_liquidity,
            max_archive_age_hours=max_archive_age_hours,
        )

    @mcp.tool(
        name="analytics.arbitrage",
        description="Scan Polymarket and optional venues for arbitrage opportunities.",
    )
    def analytics_arbitrage(min_spread: float = 0.025, venues: str = "polymarket") -> Dict[str, Any]:
        return _call_tool("analytics.arbitrage", min_spread=min_spread, venues=venues)

    @mcp.tool(
        name="analytics.risk",
        description="Assess market risk factors and return a scored explanation.",
    )
    def analytics_risk(market: str) -> Dict[str, Any]:
        return _call_tool("analytics.risk", market=market)

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
        name="archive.manifest",
        description="List local research archive datasets and quality flags.",
    )
    def archive_manifest(dataset: str = "latest") -> Dict[str, Any]:
        return _call_tool("archive.manifest", dataset=dataset)

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

    @mcp.tool(
        name="wallet.whale_trades",
        description="Return top public trade rows by notional value for a recent time window.",
    )
    def wallet_whale_trades(
        limit: int = 5,
        hours: int = 24,
        min_notional: float = 0,
        sample_size: int = 1000,
    ) -> Dict[str, Any]:
        return _call_tool(
            "wallet.whale_trades",
            limit=limit,
            hours=hours,
            min_notional=min_notional,
            sample_size=sample_size,
        )

    @mcp.tool(
        name="wallet.smart_money",
        description="Return locally identified high win-rate smart-money wallets ranked by edge score.",
    )
    def wallet_smart_money(min_win_rate: float = 0.70, min_trades: int = 10, limit: int = 20) -> Dict[str, Any]:
        return _call_tool("wallet.smart_money", min_win_rate=min_win_rate, min_trades=min_trades, limit=limit)

    @mcp.tool(
        name="trader.leaderboard",
        description="Return active traders with recent volume and closed-position win-rate evidence.",
    )
    def trader_leaderboard(
        limit: int = 3,
        hours: int = 72,
        min_win_rate: float = 0.8,
        candidate_count: int = 25,
    ) -> Dict[str, Any]:
        return _call_tool(
            "trader.leaderboard",
            limit=limit,
            hours=hours,
            min_win_rate=min_win_rate,
            candidate_count=candidate_count,
        )

    @mcp.tool(
        name="alerts.create_price_rule",
        description="Create a local price alert rule.",
    )
    def alerts_create_price_rule(
        market: str,
        above: float = 0,
        below: float = 0,
        dry_run: bool = True,
        confirm: bool = False,
    ) -> Dict[str, Any]:
        above_value = above if above else None
        below_value = below if below else None
        return _call_tool(
            "alerts.create_price_rule",
            market=market,
            above=above_value,
            below=below_value,
            dry_run=dry_run,
            confirm=confirm,
        )

    @mcp.tool(
        name="watch.scheduled_scan",
        description="Run a bounded scheduled scan workflow.",
    )
    def watch_scheduled_scan(market: str = "", schedule: str = "", runs: int = 1) -> Dict[str, Any]:
        return _call_tool("watch.scheduled_scan", market=market, schedule=schedule, runs=runs)

    return mcp


def main(transport: str = "stdio", mount_path: Optional[str] = None) -> int:
    """Run PolyTerm's FastMCP server."""
    server = create_server()
    server.run(transport=transport, mount_path=mount_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
