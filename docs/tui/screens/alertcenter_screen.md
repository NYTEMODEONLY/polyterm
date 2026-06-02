# Alert Center Screen

> Unified view of all alerts and notifications with management options.

## Overview

The Alert Center provides a centralized hub for viewing and managing all PolyTerm alerts. It offers options to view active alerts, check for new ones, see acknowledged alerts, or clear all alerts at once.

## Access

- **Menu shortcut**: `ac`, `center`, `alertcenter`
- **Menu path**: Extended shortcuts menu

## What It Shows

A simple options menu with four actions:

1. **View active alerts** -- shows current unacknowledged alerts
2. **Check for new alerts** -- scans for newly triggered alerts
3. **View all (incl. acknowledged)** -- shows the full alert history
4. **Clear all alerts** -- removes all stored alerts

## Navigation / Keyboard Shortcuts

- `1`-`4` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| View active | `polyterm center` |
| Check new | `polyterm center --check` |
| View all | `polyterm center --all` |
| Clear all | `polyterm center --clear` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)

## Related Screens

- [alerts_screen](../screens/alerts_screen.md) -- the numbered-menu alerts screen with type filtering and notification testing

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
