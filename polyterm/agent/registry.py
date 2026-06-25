"""Registry for agent-safe PolyTerm tools."""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..cli.lazy_group import LAZY_COMMANDS


@dataclass(frozen=True)
class AgentTool:
    """Metadata for one tool exposed to external agents."""

    name: str
    description: str
    command: str
    args: Dict[str, Any] = field(default_factory=dict)
    schema: str = ""
    read_only: bool = True
    mutates_local_state: bool = False
    requires_confirmation: bool = False
    may_prompt: bool = False
    long_running: bool = False
    adapter_available: bool = True
    live_data: bool = True
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "command": self.command,
            "args": self.args,
            "schema": self.schema,
            "read_only": self.read_only,
            "mutates_local_state": self.mutates_local_state,
            "requires_confirmation": self.requires_confirmation,
            "may_prompt": self.may_prompt,
            "long_running": self.long_running,
            "adapter_available": self.adapter_available,
            "live_data": self.live_data,
            "examples": self.examples,
        }


TOOLS: List[AgentTool] = [
    AgentTool(
        name="agent.schemas",
        description="Return rich input/output schemas and safety metadata for one or all PolyTerm tools.",
        command="polyterm agent schemas --format json",
        args={"tool": "string"},
        schema="docs/schemas/agent.schemas.schema.json",
    ),
    AgentTool(
        name="agent.doctor",
        description="Diagnose PolyTerm agent installation, schemas, manifests, MCP boot, APIs, and archive health.",
        command="polyterm agent doctor --format json",
        args={"skip_network": "boolean"},
        schema="docs/schemas/agent.doctor.schema.json",
    ),
    AgentTool(
        name="market.search",
        description="Search active Polymarket markets by query.",
        command="polyterm search {query} --format json",
        args={"query": "string", "limit": "integer"},
        schema="docs/schemas/market.search.schema.json",
    ),
    AgentTool(
        name="market.resolve",
        description="Resolve a slug, URL, Gamma ID, condition ID, or token ID into market identifiers.",
        command="polyterm lookup {identifier} --format json",
        args={"identifier": "string"},
        schema="docs/schemas/market.resolve.schema.json",
    ),
    AgentTool(
        name="market.top",
        description="Return the top active Polymarket markets from live Gamma market data.",
        command="polyterm agent jsonl-server tool=market.top",
        args={"limit": "integer", "sort": "string"},
        schema="docs/schemas/market.top.schema.json",
        examples=[
            "What are the top 3 Polymarket markets today?",
            "Show the most active markets right now.",
        ],
    ),
    AgentTool(
        name="market.orderbook",
        description="Return order book and spread analysis for a CLOB token ID.",
        command="polyterm orderbook {token_id} --format json",
        args={"token_id": "string", "depth": "integer"},
        schema="docs/schemas/market.orderbook.schema.json",
    ),
    AgentTool(
        name="market.price_history",
        description="Return CLOB-backed price history for a market.",
        command="polyterm chart --market {market} --format json",
        args={"market": "string", "hours": "integer"},
        schema="docs/schemas/market.price_history.schema.json",
    ),
    AgentTool(
        name="market.movers",
        description="Return active markets that flipped or had large available price changes.",
        command="polyterm agent jsonl-server tool=market.movers",
        args={"limit": "integer", "hours": "integer", "min_abs_change": "number"},
        schema="docs/schemas/market.movers.schema.json",
        examples=[
            "What markets have flipped or spiked in the last 48 hours?",
            "Show the biggest Polymarket movers.",
        ],
    ),
    AgentTool(
        name="market.research",
        description="Generate a flagship one-call market research brief with thesis, evidence, gaps, and workflow.",
        command="polyterm research --market {market} --format json",
        args={
            "market": "string",
            "prefetch_whales": "boolean",
            "min_notional": "number",
            "hours": "integer",
            "limit": "integer",
            "persist": "boolean",
        },
        schema="docs/schemas/market.research.schema.json",
    ),
    AgentTool(
        name="market.explain_move",
        description="Explain a recent YES price move with CLOB price history, order book context, and quality flags.",
        command="polyterm explain-move --market {market} --format json",
        args={"market": "string", "hours": "integer"},
        schema="docs/schemas/market.explain_move.schema.json",
    ),
    AgentTool(
        name="market.compare",
        description="Compare markets side by side with YES price gaps, recent moves, liquidity, and evidence quality flags.",
        command="polyterm compare --markets <market> --markets <market> --format json",
        args={"markets": "array", "hours": "integer"},
        schema="docs/schemas/market.compare.schema.json",
    ),
    AgentTool(
        name="scan.opportunities",
        description="Scan active markets for unusual moves, stale archive coverage, and research-worthy opportunities.",
        command="polyterm scan-opportunities --query <query> --format json",
        args={
            "query": "string",
            "limit": "integer",
            "min_volume": "number",
            "min_liquidity": "number",
            "max_archive_age_hours": "integer",
        },
        schema="docs/schemas/scan.opportunities.schema.json",
    ),
    AgentTool(
        name="analytics.arbitrage",
        description="Scan Polymarket and optional venues for arbitrage opportunities.",
        command="polyterm arbitrage --format json",
        args={"min_spread": "number", "venues": "string"},
        schema="docs/schemas/analytics.arbitrage.schema.json",
    ),
    AgentTool(
        name="analytics.risk",
        description="Assess market risk factors and return a scored explanation.",
        command="polyterm risk --market {market} --format json",
        args={"market": "string"},
        schema="docs/schemas/analytics.risk.schema.json",
    ),
    AgentTool(
        name="archive.search",
        description="Search locally archived PolyTerm research briefs.",
        command="polyterm archive search --query {query} --format json",
        args={"query": "string", "limit": "integer"},
        schema="docs/schemas/archive.search.schema.json",
    ),
    AgentTool(
        name="archive.status",
        description="Report local archive coverage, freshness, and recommended refresh actions.",
        command="polyterm archive status --query {query} --format json",
        args={"query": "string", "market_id": "string", "max_age_hours": "integer"},
        schema="docs/schemas/archive.status.schema.json",
    ),
    AgentTool(
        name="wallet.inspect",
        description="Inspect a wallet using public Data API and local PolyTerm evidence.",
        command="polyterm wallets --analyze {address} --refresh --format json",
        args={"address": "string"},
        schema="docs/schemas/wallet.inspect.schema.json",
    ),
    AgentTool(
        name="wallet.whales",
        description="Return wallet-level whale activity and smart-money candidates.",
        command="polyterm whales --wallets --format json",
        args={"min_notional": "number", "hours": "integer", "limit": "integer"},
        schema="docs/schemas/wallet.whales.schema.json",
    ),
    AgentTool(
        name="wallet.whale_trades",
        description="Return top public trade rows by notional value for a recent time window.",
        command="polyterm agent jsonl-server tool=wallet.whale_trades",
        args={"limit": "integer", "hours": "integer", "min_notional": "number"},
        schema="docs/schemas/wallet.whale_trades.schema.json",
        examples=[
            "Give me the top 5 whale trades in the last 24 hours and the markets they were placed in.",
        ],
    ),
    AgentTool(
        name="wallet.smart_money",
        description="Return locally identified high win-rate smart-money wallets ranked by edge score.",
        command="polyterm wallets --type smart --format json",
        args={"min_win_rate": "number", "min_trades": "integer", "limit": "integer"},
        schema="docs/schemas/wallet.smart_money.schema.json",
    ),
    AgentTool(
        name="trader.leaderboard",
        description="Return active traders with recent volume and closed-position win-rate evidence.",
        command="polyterm leaderboard --source data-api --format json",
        args={"limit": "integer", "hours": "integer", "min_win_rate": "number"},
        schema="docs/schemas/trader.leaderboard.schema.json",
        examples=[
            "Give me the top 3 traders in the last 72 hours with an 80%+ win rate.",
        ],
    ),
    AgentTool(
        name="analytics.thesis",
        description="Generate an explainable market-level trade thesis.",
        command="polyterm thesis --market {market} --format json",
        args={"market": "string"},
        schema="docs/schemas/analytics.thesis.schema.json",
    ),
    AgentTool(
        name="archive.manifest",
        description="List local research archive datasets and quality flags.",
        command="polyterm export --dataset latest --format json",
        args={"dataset": "string"},
        schema="docs/schemas/archive.manifest.schema.json",
    ),
    AgentTool(
        name="alerts.create_price_rule",
        description="Create a local price alert rule.",
        command="polyterm alerts --add-rule price --market {market} --above {above} --below {below} --format json",
        args={"market": "string", "above": "number", "below": "number", "dry_run": "boolean", "confirm": "boolean"},
        schema="docs/schemas/alerts.create_price_rule.schema.json",
        read_only=False,
        mutates_local_state=True,
        requires_confirmation=True,
        live_data=False,
    ),
    AgentTool(
        name="watch.scheduled_scan",
        description="Run a long-running scheduled scan with optional notifications.",
        command="polyterm watch --market {market} --schedule {schedule} --runs {runs} --format json",
        args={"market": "string", "schedule": "string", "runs": "integer"},
        schema="docs/schemas/watch.scheduled_scan.schema.json",
        long_running=True,
    ),
]


def get_tools() -> List[AgentTool]:
    """Return all public agent tools."""
    return list(TOOLS)


def get_manifest() -> Dict[str, Any]:
    """Return the machine-readable agent tool manifest."""
    return {
        "name": "polyterm",
        "schema_version": "2026-06-25",
        "description": "No-custody Polymarket intelligence, wallet, research, alert, and CLI tools.",
        "adapters": {
            "mcp": {
                "command": "polyterm agent mcp-server",
                "transport": "stdio",
                "optional_extra": "mcp",
                "install": 'pip install -e ".[mcp]"',
                "tool_count": len(TOOLS),
            },
            "json_lines": {
                "command": "polyterm agent jsonl-server",
                "transport": "stdio-json-lines",
                "optional_extra": None,
                "tool_count": len(TOOLS),
            },
        },
        "tools": [tool.to_dict() for tool in TOOLS],
        "cli_commands": get_cli_command_catalog(),
    }


def get_cli_command_catalog() -> List[Dict[str, Any]]:
    """Return all PolyTerm CLI commands so agents can discover the full suite."""
    rows = [
        {
            "name": name,
            "module": module,
            "attribute": attr,
            "command": f"polyterm {name} --help",
            "doc": f"docs/cli/{name}.md",
            "adapter_available": False,
            "notes": "Use the CLI help and command docs for exact options. Prefer manifest tools for stable adapter calls.",
        }
        for name, (module, attr) in sorted(LAZY_COMMANDS.items())
    ]
    rows.append({
        "name": "update",
        "module": "polyterm.cli.main",
        "attribute": "update",
        "command": "polyterm update --help",
        "doc": "docs/cli/update.md",
        "adapter_available": False,
        "notes": "Checks package updates and may prompt before installing.",
    })
    return sorted(rows, key=lambda row: row["name"])
