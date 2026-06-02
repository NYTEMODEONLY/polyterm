# Chart Screen

> View ASCII price history charts for any market.

## Overview

The Chart screen generates terminal-based price visualizations for a given market. It supports both full line charts and compact sparkline views, with a configurable time window for the historical data displayed.

## Access

- **Menu shortcut**: `ch` or `chart`
- **Menu path**: Type shortcut from either page

## What It Shows

- ASCII line chart of price movement over time (using Bresenham's algorithm)
- Sparkline view as a compact alternative (8-level block characters)
- Customizable timeframe in hours

## Navigation / Keyboard Shortcuts

- Prompted for market ID or search term
- Prompted for hours of history (default: 24)
- Prompted for view type: `chart` or `sparkline`
- Returns to menu when the command completes

## CLI Command

```bash
polyterm chart -m <market> -h <hours>
polyterm chart -m <market> -h <hours> --sparkline
```

## Data Sources

- CLOB `/prices-history` endpoint for real market price data
- Falls back to local SQLite database snapshots if CLOB data is unavailable

## Related Screens

- [Compare](../screens/compare_screen.md) - compare charts across multiple markets
- [Stats](../screens/stats_screen.md) - numerical statistics for the same market data
- [Depth](../screens/depth_screen.md) - current order book depth analysis

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
