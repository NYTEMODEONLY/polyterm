# Presets Screen

> Save and reuse screener filter combinations.

## Overview

The Presets screen lets you manage saved search filter presets for the market screener. You can create, list, run, view, and delete presets, allowing you to quickly re-run common screening criteria without re-entering filters each time.

## Access

- **Menu shortcut**: `pr` or `presets`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A numbered menu with five options:

1. **List saved presets** -- shows all stored presets
2. **Create new preset** -- launches interactive preset creation
3. **Run a preset** -- prompts for a preset name and executes it
4. **View preset details** -- prompts for a name and shows its filters
5. **Delete a preset** -- prompts for a name and removes it

## Navigation / Keyboard Shortcuts

- Enter a number `1`-`5` to select an action
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| List presets | `polyterm presets --list` |
| Create preset | `polyterm presets --interactive` |
| Run preset | `polyterm presets --run <name>` |
| View preset | `polyterm presets --view <name>` |
| Delete preset | `polyterm presets --delete <name>` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for stored presets
- Gamma API when running a preset (executes the saved screener filters)

## Related Screens

- [Screener Screen](../screens/screener_screen.md)
- [Search / Advanced Search](../screens/notes.md)

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
