"""Registry for agent-safe PolyTerm tools."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


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
        }


TOOLS: List[AgentTool] = [
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
        args={"min_notional": "number", "hours": "integer"},
        schema="docs/schemas/wallet.whales.schema.json",
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
        command="polyterm alerts --add-rule price --market {market} --above {price} --format json",
        args={"market": "string", "above": "number", "below": "number"},
        schema="docs/schemas/alerts.create_price_rule.schema.json",
        read_only=False,
        mutates_local_state=True,
        requires_confirmation=False,
    ),
    AgentTool(
        name="watch.scheduled_scan",
        description="Run a long-running scheduled scan with optional notifications.",
        command="polyterm watch --schedule {schedule} --format json",
        args={"market": "string", "schedule": "string"},
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
        "schema_version": "2026-06-02",
        "description": "No-custody Polymarket intelligence, wallet, research, and alert tools.",
        "tools": [tool.to_dict() for tool in TOOLS],
    }
