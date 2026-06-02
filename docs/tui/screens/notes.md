# Market Notes

> Manage research notes and trading theses for individual markets.

## Overview

The Notes screen provides a way to track your personal research and thesis on Polymarket markets. You can list, add, view, and delete notes attached to specific markets. Notes are stored locally in the SQLite database.

## Access

- **Menu shortcut**: `nt` or `notes`
- **Menu path**: Page 2 → Notes

## What It Shows

A menu with four operations:

1. **List all notes** -- displays every saved note
2. **Add/edit note for a market** -- searches for a market and attaches a note
3. **View specific note** -- look up a note by market ID or search term
4. **Delete a note** -- remove a note by market ID

## Navigation / Keyboard Shortcuts

No special keyboard shortcuts. Standard numbered menu selection (`1`-`4`, `b` to go back).

## CLI Commands

| Option | CLI command |
|--------|-------------|
| List all | `polyterm notes --list` |
| Add/edit | `polyterm notes --add <search>` |
| View | `polyterm notes --view <search>` |
| Delete | `polyterm notes --delete <market_id>` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)

## Related Screens

- [Bookmarks](../screens/bookmarks.md)
- [Position Tracker](../screens/position_screen.md)

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
