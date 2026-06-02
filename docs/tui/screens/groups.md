# Watchlist Groups

> Organize markets into named collections.

## Overview

The Groups screen lets you create and manage named collections of markets. You can group related markets together (e.g., "US Elections", "Crypto Bets") for quick access and organized tracking. Groups are stored locally in the SQLite database.

## Access

- **Menu shortcut**: `gr` or `groups`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A menu with six management options:

1. **List all groups** -- shows all created groups
2. **Create new group** -- create a group with a name
3. **View group markets** -- see all markets in a specific group
4. **Add market to group** -- add a market to an existing group
5. **Remove market from group** -- remove a market from a group
6. **Delete group** -- permanently remove a group

## Navigation / Keyboard Shortcuts

- `1`-`6` -- Select an option
- `b` -- Back to main menu

## CLI Command

```bash
polyterm groups --list                          # List all groups
polyterm groups --create <name>                 # Create a new group
polyterm groups --view <name>                   # View group markets
polyterm groups --add <group> -m <market>       # Add market to group
polyterm groups --remove <group> -m <market>    # Remove market from group
polyterm groups --delete <name>                 # Delete a group
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for group storage
- Gamma API for market data when viewing group contents

## Related Screens

- [Export](../screens/export.md) -- export data for grouped markets
- [History](../screens/history.md) -- view history for markets in a group

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
