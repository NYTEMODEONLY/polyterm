# Spread Screen

> Understand bid/ask spread and execution costs for a market.

## Overview

The Spread screen analyzes the bid/ask spread and estimated execution costs for a given market at a specified trade amount. This helps users understand the true cost of entering or exiting a position, beyond just the displayed price.

## Access

- **Menu shortcut**: `sp`, `spread`
- **Menu path**: Page 2 (Spread)

## What It Shows

After prompting for a market name and trade amount, it displays:

- Current bid/ask spread
- Spread percentage
- Estimated slippage at the specified trade size
- Execution cost analysis

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. The user enters a market name and trade amount at the prompts; leaving the market name empty returns to the menu.

## CLI Command

```bash
polyterm spread "<market>" --amount <USD>
```

Default trade amount is `100` USD.

## Data Sources

- CLOB API (order book data for spread calculation)

## Related Screens

- [size_screen](../screens/size_screen.md) -- position sizing calculator
- [simulate_screen](../screens/simulate_screen.md) -- P&L simulation with fee impact

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
