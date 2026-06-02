# Calendar Screen

> View upcoming market resolutions to plan trades and exits.

## Overview

The Calendar screen displays markets that are approaching their resolution date. This helps traders plan ahead by showing which markets are ending soon, enabling timely exits or last-minute entries before resolution.

## Access

- **Menu shortcut**: `cal` or `calendar`
- **Menu path**: Type shortcut from either page

## What It Shows

- Markets grouped by resolution date
- Countdown to each market's resolution
- Configurable lookahead window (defaults to 7 days)

## Navigation / Keyboard Shortcuts

- Prompted for number of days to look ahead (default: 7)
- Returns to menu when the command completes

## CLI Command

```bash
polyterm calendar --days <days>
```

## Data Sources

- Gamma REST API (market end dates and metadata)

## Related Screens

- [Dashboard](../screens/dashboard_screen.md) - also shows upcoming activity
- [Chart](../screens/chart_screen.md) - view price history before resolution

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
