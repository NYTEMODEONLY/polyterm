# Notification Settings

> Configure how you receive alerts (desktop, sound, webhook).

## Overview

The Notify screen lets you view and modify notification delivery settings. You can enable or disable desktop and sound notifications, configure a webhook URL for external integrations, and test that notifications are working.

## Access

- **Menu shortcut**: `nf` or `notify`
- **Menu path**: Page 2 → Notify

## What It Shows

A menu of six options for managing notification channels:

1. **View current settings** -- shows which channels are enabled
2. **Interactive configuration** -- guided setup wizard
3. **Test notifications** -- sends a test notification to verify delivery
4. **Enable/disable desktop** -- toggle desktop notifications
5. **Enable/disable sound** -- toggle sound notifications
6. **Configure webhook** -- set a webhook URL for external delivery

## Navigation / Keyboard Shortcuts

Standard numbered menu (`1`-`6`, `b` to go back). Options 4 and 5 prompt a follow-up enable/disable choice.

## CLI Commands

| Option | CLI command |
|--------|-------------|
| View settings | `polyterm notify --status` |
| Interactive config | `polyterm notify --configure` |
| Test | `polyterm notify --test` |
| Enable channel | `polyterm notify --enable <desktop\|sound>` |
| Disable channel | `polyterm notify --disable <desktop\|sound>` |
| Set webhook | `polyterm notify --webhook <url>` |

## Data Sources

- Config file (`~/.polyterm/config.toml`)

## Related Screens

- [Price Alerts](../screens/pricealert.md)
- [Alert Center](../screens/alertcenter_screen.md)

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
