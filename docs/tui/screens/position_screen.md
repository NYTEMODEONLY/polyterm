# Position Tracker

> Track trades manually without connecting a wallet.

## Overview

The Position Tracker lets you record and manage trades locally. You can add positions with entry prices, view open or closed positions, close out positions, and see a P&L summary. No wallet connection is required -- all data is stored in the local SQLite database.

## Access

- **Menu shortcut**: `pos` or `position`
- **Menu path**: Page 2 → Position

## What It Shows

A menu with six operations:

1. **View all positions** -- list every recorded position (open and closed)
2. **View open positions only** -- filter to active positions
3. **View closed positions** -- filter to resolved/exited positions
4. **Add new position** -- interactive position entry
5. **Close a position** -- mark a position as closed by ID
6. **View P&L summary** -- aggregate profit/loss across all positions

## Navigation / Keyboard Shortcuts

Standard numbered menu (`1`-`6`, `b` to go back).

## CLI Commands

| Option | CLI command |
|--------|-------------|
| All positions | `polyterm position --list` |
| Open only | `polyterm position --list --open` |
| Closed only | `polyterm position --list --closed` |
| Add (interactive) | `polyterm position --interactive` |
| Close | `polyterm position --close <id>` |
| P&L summary | `polyterm position --summary` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)

## Related Screens

- [P&L Tracker](../screens/pnl_screen.md)
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
