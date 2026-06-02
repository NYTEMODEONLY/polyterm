# Alerts Screen

> View, filter, acknowledge, and test delivery of alerts.

## Overview

The Alerts screen is the full-featured alert management interface. It supports viewing all or unread alerts, filtering by type (whale, insider, arbitrage, smart_money), acknowledging individual alerts by ID, and sending test notifications to Telegram and Discord.

## Access

- **Menu shortcut**: `12`, `alert`
- **Menu path**: Page 1 item 12 (Alerts)

## What It Shows

A submenu with six operations:

1. **View All Alerts** -- recent alerts of all types (configurable limit)
2. **View Unread** -- only unacknowledged alerts
3. **Filter by Type** -- whale, insider, arbitrage, or smart_money
4. **Acknowledge Alert** -- mark a specific alert as read by ID
5. **Test Telegram** -- send a test notification to Telegram
6. **Test Discord** -- send a test notification to Discord

## Navigation / Keyboard Shortcuts

- `1`-`6` to select an operation
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| View all | `polyterm alerts --limit=N` |
| Unread | `polyterm alerts --unread --limit=N` |
| Filter by type | `polyterm alerts --type=TYPE --limit=N` |
| Acknowledge | `polyterm alerts --ack=ID` |
| Test Telegram | `polyterm alerts --test-telegram` |
| Test Discord | `polyterm alerts --test-discord` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)
- Telegram / Discord APIs (for test notifications)

## Related Screens

- [alertcenter_screen](../screens/alertcenter_screen.md) -- simplified alert center view

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
