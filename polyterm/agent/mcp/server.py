"""Small MCP-ready JSON server for PolyTerm agent tools.

This module deliberately avoids adding a mandatory MCP package dependency. It
exposes a simple JSON-lines stdio adapter and keeps the callable tool functions
in small modules so a future FastMCP wrapper can import the same functions.
"""

import json
import sys
from typing import Callable, Dict

from ..contracts import envelope, error_envelope
from ..registry import get_manifest
from .tools import analytics, archive, market, wallet


TOOL_HANDLERS: Dict[str, Callable[..., dict]] = {
    "market.search": market.search,
    "market.resolve": market.resolve,
    "market.research": market.research,
    "analytics.arbitrage": analytics.arbitrage,
    "analytics.thesis": analytics.thesis,
    "archive.search": archive.search,
    "archive.status": archive.status,
    "wallet.inspect": wallet.inspect,
    "wallet.whales": wallet.whales,
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
