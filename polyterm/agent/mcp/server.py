"""Small JSON-lines server for PolyTerm agent tools.

This module deliberately avoids adding a mandatory MCP package dependency. It
exposes a simple JSON-lines stdio adapter and keeps the callable tool functions
in small modules shared with the standard FastMCP wrapper.
"""

import json
import sys
from typing import Callable, Dict

from ..contracts import envelope, error_envelope
from ..registry import get_manifest
from .tools import alerts, analytics, archive, live, market, meta, scan, wallet, watch


TOOL_HANDLERS: Dict[str, Callable[..., dict]] = {
    "market.search": market.search,
    "agent.schemas": meta.schemas,
    "agent.doctor": meta.doctor,
    "market.resolve": market.resolve,
    "market.top": live.top_markets,
    "market.orderbook": market.orderbook,
    "market.price_history": market.price_history,
    "market.movers": live.market_movers,
    "market.research": market.research,
    "market.explain_move": market.explain_move,
    "market.compare": market.compare,
    "scan.opportunities": scan.opportunities,
    "analytics.arbitrage": analytics.arbitrage,
    "analytics.risk": analytics.risk,
    "analytics.thesis": analytics.thesis,
    "archive.search": archive.search,
    "archive.status": archive.status,
    "archive.manifest": archive.manifest,
    "wallet.inspect": wallet.inspect,
    "wallet.whales": wallet.whales,
    "wallet.whale_trades": live.whale_trades,
    "wallet.smart_money": wallet.smart_money,
    "trader.leaderboard": live.top_traders,
    "alerts.create_price_rule": alerts.create_price_rule,
    "watch.scheduled_scan": watch.scheduled_scan,
}


def handle_request(request: dict) -> dict:
    """Handle one JSON request."""
    if request.get("method") == "manifest":
        return envelope(get_manifest(), meta={"tool": "agent.manifest"})

    tool_name = request.get("tool")
    args = request.get("args") or {}
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return error_envelope(f"Unknown tool: {tool_name}")

    try:
        return handler(**args)
    except Exception as exc:
        return error_envelope(str(exc), meta={"tool": tool_name})


def main() -> int:
    """Run a JSON-lines stdio server."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except Exception as exc:
            response = error_envelope(str(exc))
        print(json.dumps(response, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
