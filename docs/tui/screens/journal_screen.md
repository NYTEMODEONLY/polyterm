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
