# Pinned Markets

> Quick access to your most important markets.

## Overview

The Pinned Markets screen lets you maintain a shortlist of markets you want to track closely. Pinned markets are stored locally and can be refreshed with current prices on demand. This is a lighter-weight alternative to bookmarks, designed for fast access to a small set of active markets.

## Access

- **Menu shortcut**: `pin` or `pinned`
- **Menu path**: Page 2 → Pinned

## What It Shows

A menu with five operations:

1. **View pinned markets** -- list all pinned markets with their current data
2. **Pin a new market** -- add a market by name/search
3. **Refresh prices** -- update prices for all pinned markets
4. **Unpin a market** -- remove a market by pin ID
5. **Clear all pins** -- remove every pinned market

## Navigation / Keyboard Shortcuts

Standard numbered menu (`1`-`5`, `b` to go back).

## CLI Commands

| Option | CLI command |
|--------|-------------|
| View pins | `polyterm pin` |
| Pin market | `polyterm pin <market>` |
| Refresh | `polyterm pin --refresh` |
| Unpin | `polyterm pin --unpin <id>` |
| Clear all | `polyterm pin --clear` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)
- Gamma REST API for price refresh

## Related Screens

- [Bookmarks](../screens/bookmarks.md)
- [Recently Viewed](../screens/recent.md)

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
