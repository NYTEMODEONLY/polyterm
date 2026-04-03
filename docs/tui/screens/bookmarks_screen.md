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
