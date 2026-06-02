# Bookmarks Screen

> Save and manage favorite markets for quick access.

## Overview

The Bookmarks screen lets you view saved market bookmarks, add new ones by market name, or enter interactive mode for full bookmark management (add, remove, annotate). Bookmarks are stored locally in the SQLite database.

## Access

- **Menu shortcut**: `17`, `bm`, `bookmarks`
- **Menu path**: Page 1 item 17 (Bookmarks)

## What It Shows

A three-option menu:

1. **View bookmarks** -- list all saved bookmarks
2. **Add a bookmark** -- search for a market by name and bookmark it
3. **Interactive mode** -- full-featured bookmark management (add, remove, notes)

## Navigation / Keyboard Shortcuts

- `1`, `2`, `3` to select an option
- `q` to return to the main menu
- Press Enter after command output to return to menu

## CLI Commands

| Option | Command |
|--------|---------|
| View | `polyterm bookmarks --list` |
| Add | `polyterm bookmarks --add "MARKET_NAME"` |
| Interactive | `polyterm bookmarks` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`, `bookmarks` table)

## Related Screens

- [alertcenter_screen](../screens/alertcenter_screen.md) -- alerts for bookmarked markets

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
