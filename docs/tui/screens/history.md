# Market History

> View price and volume history for any market.

## Overview

The History screen lets you look up historical price and volume data for a specific market over configurable time periods. It displays the data as a chart in the terminal. You enter a market name or ID and select a time range, then the screen renders a visual history.

## Access

- **Menu shortcut**: `hist` or `history`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A two-step prompt flow:

1. **Market selection** -- enter a market name or ID
2. **Time period** -- choose from:
   - Last day
   - Last week (default)
   - Last month
   - All time

The result is an ASCII chart showing price history for the selected period.

## Navigation / Keyboard Shortcuts

- `1`-`4` -- Select time period
- No additional keyboard shortcuts; prompt-based flow

## CLI Command

```bash
polyterm history <market> --period week --chart
polyterm history <market> --period day --chart
polyterm history <market> --period month --chart
polyterm history <market> --period all --chart
```

## Data Sources

- CLOB API price history endpoint (`/prices-history`)
- Falls back to local SQLite database snapshots if CLOB data is unavailable

## Related Screens

- [Export](../screens/export.md) -- export the historical data to a file
- [Hot Markets](../screens/hot.md) -- find markets with significant recent movement

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
