# Snapshot Screen

> Save and compare market states over time.

## Overview

The Snapshot screen allows users to capture the current state of a market and save it for later comparison. This is useful for tracking how a market evolves, comparing current prices to a historical baseline, and reviewing saved snapshots.

## Access

- **Menu shortcut**: `snap`, `snapshot`
- **Menu path**: Page 2 (Snapshot)

## What It Shows

A submenu with five operations:

1. **List saved snapshots** -- view all previously saved snapshots
2. **Save new snapshot** -- capture the current state of a market
3. **View snapshot details** -- inspect a specific snapshot by ID
4. **Compare snapshot to current** -- diff a saved snapshot against live data
5. **Delete snapshot** -- remove a snapshot by ID

## Navigation / Keyboard Shortcuts

- `1` -- List snapshots
- `2` -- Save new snapshot (prompts for market name)
- `3` -- View snapshot (prompts for snapshot ID)
- `4` -- Compare snapshot to current (prompts for snapshot ID)
- `5` -- Delete snapshot (prompts for snapshot ID)
- `b` -- Back to main menu

## CLI Commands

| Option | Command |
|--------|---------|
| List | `polyterm snapshot --list` |
| Save | `polyterm snapshot --save "<market>"` |
| View | `polyterm snapshot --view <id>` |
| Compare | `polyterm snapshot --compare <id>` |
| Delete | `polyterm snapshot --delete <id>` |

## Data Sources

- Gamma REST API (live market data for saving and comparing)
- Local SQLite database (`~/.polyterm/data.db` for stored snapshots)

## Related Screens

- [stats_screen](../screens/stats_screen.md) -- detailed market statistics
