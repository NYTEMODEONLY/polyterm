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
