# P&L Tracker

> Track your profit and loss over configurable time periods.

## Overview

The P&L screen shows a detailed profit-and-loss summary for your tracked positions. You select a time period (today, week, month, year, or all time) and get a breakdown of gains, losses, and net performance. Always runs in detailed mode for maximum insight.

## Access

- **Menu shortcut**: `pnl`
- **Menu path**: Page 2 → P&L

## What It Shows

A time-period selection menu:

1. **Today** -- current day's P&L
2. **Last 7 days** -- weekly summary
3. **Last 30 days** -- monthly summary (default)
4. **Last year** -- yearly summary
5. **All time** -- complete history

The output includes detailed position-by-position P&L data.

## Navigation / Keyboard Shortcuts

Standard numbered menu (`1`-`5`, `b` to go back).

## CLI Command

```bash
polyterm pnl --period <day|week|month|year|all> --detailed
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for tracked positions
- Gamma REST API / Data API for current market prices

## Related Screens

- [Position Tracker](../screens/position_screen.md)
- [Portfolio](../screens/portfolio.md)
- [My Wallet](../screens/mywallet.md)

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
