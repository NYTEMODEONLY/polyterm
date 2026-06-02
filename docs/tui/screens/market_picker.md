# Market Picker

> Reusable component for selecting markets from a numbered list.

## Overview

The Market Picker is an internal TUI component used by other screens that need the user to select a market. It fetches active markets from the Gamma API, displays them in a numbered table with price and volume, and returns the selected market dictionary. It is not a standalone screen accessible from the menu.

## Access

- **Menu shortcut**: None (internal component)
- **Menu path**: Not directly accessible; used by other screens

## What It Shows

A table of active markets with columns:

- **#** -- selection number
- **Market** -- market title (truncated to 50 chars)
- **Price** -- YES price as a percentage
- **Volume** -- 24-hour volume (formatted as $K/$M)

Below the table, the user can enter a number to select, `m` for manual market ID entry, or `q` to cancel.

## Key Functions

| Function | Purpose |
|----------|---------|
| `fetch_markets(limit)` | Fetches active markets from Gamma API |
| `display_market_list(console, markets)` | Renders the numbered market table |
| `pick_market(console, prompt, allow_manual, limit)` | Full interactive picker flow |
| `get_market_id(market)` | Extracts market ID from a market dict |
| `get_market_title(market)` | Extracts market title from a market dict |

## Data Sources

- Gamma REST API (`GammaClient.get_markets()`)

## Related Screens

- [live_monitor](../screens/live_monitor.md) -- uses its own market search (not this picker)
- [monitor](../screens/monitor.md) -- category-based market selection

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
