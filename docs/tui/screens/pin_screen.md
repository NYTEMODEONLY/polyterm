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
