# Digest Screen

> Get a summary of trading and market activity for a selected time period.

## Overview

The Digest screen generates a condensed summary of market and trading activity over a chosen time window. It supports today, yesterday, this week, or this month as time periods, giving a quick recap without needing to dig through individual screens.

## Access

- **Menu shortcut**: `dig` or `digest`
- **Menu path**: Type shortcut from either page

## What It Shows

- Summary of market activity for the selected period
- Key trading metrics and notable events

## Navigation / Keyboard Shortcuts

- **1** - Today (default)
- **2** - Yesterday
- **3** - This week
- **4** - This month
- **b** - Back to menu

## CLI Command

```bash
polyterm digest --period today
polyterm digest --period yesterday
polyterm digest --period week
polyterm digest --period month
```

## Data Sources

- Gamma REST API (market activity data)
- Local SQLite database (tracked activity and history)

## Related Screens

- [Dashboard](../screens/dashboard_screen.md) - real-time activity overview
- [Calendar](../screens/calendar_screen.md) - upcoming market resolutions

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
