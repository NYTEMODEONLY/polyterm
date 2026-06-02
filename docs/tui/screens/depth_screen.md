# Depth Screen

> Analyze order book depth and estimate slippage for a given trade size.

## Overview

The Depth screen shows liquidity at each price level in a market's order book and estimates how much slippage to expect for a specified trade size. This helps traders understand the true cost of entering or exiting a position.

## Access

- **Menu shortcut**: `dp` or `depth`
- **Menu path**: Type shortcut from either page

## What It Shows

- Order book depth at each price level
- Liquidity distribution across bids and asks
- Slippage estimate for the specified trade size

## Navigation / Keyboard Shortcuts

- Prompted for a market search term
- Prompted for trade size in dollars (default: $1000)
- Returns to menu when the command completes

## CLI Command

```bash
polyterm depth --market <search> --size <amount>
```

## Data Sources

- CLOB REST API (order book data)

## Related Screens

- [Order Book](../screens/orderbook_screen.md) - real-time order book with WebSocket feed
- [Fees](../screens/fees_screen.md) - fee and slippage calculator
- [Chart](../screens/chart_screen.md) - price history visualization

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm the linked source file still exists and the module name has not changed.
- Update command examples, TUI shortcuts, and option names when Click or controller routing changes.
- Keep data-source notes current with the active Polymarket API contracts.
- Prefer concrete endpoint names, identifier types, and output fields over broad marketing language.
- Run `./test_all_commands.sh` when a CLI command or shortcut is affected.
- Run `.venv/bin/python scripts/validate_docs.py` before committing documentation changes.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Examples should be copy-pasteable from the repository root unless stated otherwise.
- Pages for view-only workflows should say so when wallet or trading context is involved.
- Pages that depend on live market data should name Gamma, Data API, or CLOB as the source.
- Alias pages should point to the canonical page and explain why the alias exists.
- New modules should have a dedicated page rather than relying only on the index.
