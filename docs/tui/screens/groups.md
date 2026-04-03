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
