# Journal Screen

> Trade journal for documenting trades and learning from experience.

## Overview

The Journal Screen provides access to a personal trade journal where you can log trades, review past entries, and search by keyword or tag. It helps build discipline by encouraging post-trade reflection.

## Access

- **Menu shortcut**: `jn`, `journal`
- **Menu path**: Extended shortcuts menu

## What It Shows

An options menu with four actions:

1. **View recent entries** -- lists recent journal entries
2. **Add new entry** -- create a new trade journal entry
3. **Search entries** -- search entries by keyword
4. **View by tag** -- filter entries by a specific tag

## Navigation / Keyboard Shortcuts

- `1`-`4` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| View recent | `polyterm journal --list` |
| Add new | `polyterm journal --add` |
| Search | `polyterm journal --search <query>` |
| Filter by tag | `polyterm journal --tag <tag>` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)

## Related Screens

- [mywallet_screen](../screens/mywallet_screen.md) -- view wallet positions and trade history

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
