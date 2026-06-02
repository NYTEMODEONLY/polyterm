# Dashboard Screen

> Quick overview of market activity, bookmarks, alerts, and followed wallets.

## Overview

The Dashboard screen provides a consolidated snapshot of your PolyTerm activity. It clears the terminal and displays top volume markets, bookmarked markets, active alerts, and followed wallets in a single view. Designed for daily check-ins.

## Access

- **Menu shortcut**: `d`, `dash`, or `dashboard`
- **Menu path**: Page 1 (listed as "Dashboard")

## What It Shows

- Top markets by volume
- Bookmarked markets and their current status
- Active price alerts
- Followed wallet activity summaries

## Navigation / Keyboard Shortcuts

- No interactive prompts; the dashboard renders immediately
- Press Enter to return to the main menu

## CLI Command

```bash
polyterm dashboard
```

## Data Sources

- Gamma REST API (market data and volumes)
- Local SQLite database (bookmarks, alerts, followed wallets)

## Related Screens

- [Monitor](../screens/monitor_screen.md) - detailed market monitoring
- [Alerts](../screens/alerts_screen.md) - manage price alerts
- [Bookmarks](../screens/bookmarks_screen.md) - manage saved markets

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
