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
