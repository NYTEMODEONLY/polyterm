# Position Tracker

> Track trades manually without connecting a wallet.

## Overview

The Position Tracker lets you record and manage trades locally. You can add positions with entry prices, view open or closed positions, close out positions, and see a P&L summary. No wallet connection is required -- all data is stored in the local SQLite database.

## Access

- **Menu shortcut**: `pos` or `position`
- **Menu path**: Page 2 → Position

## What It Shows

A menu with six operations:

1. **View all positions** -- list every recorded position (open and closed)
2. **View open positions only** -- filter to active positions
3. **View closed positions** -- filter to resolved/exited positions
4. **Add new position** -- interactive position entry
5. **Close a position** -- mark a position as closed by ID
6. **View P&L summary** -- aggregate profit/loss across all positions

## Navigation / Keyboard Shortcuts

Standard numbered menu (`1`-`6`, `b` to go back).

## CLI Commands

| Option | CLI command |
|--------|-------------|
| All positions | `polyterm position --list` |
| Open only | `polyterm position --list --open` |
| Closed only | `polyterm position --list --closed` |
| Add (interactive) | `polyterm position --interactive` |
| Close | `polyterm position --close <id>` |
| P&L summary | `polyterm position --summary` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)

## Related Screens

- [P&L Tracker](../screens/pnl_screen.md)
- [Portfolio](../screens/portfolio.md)
- [My Wallet](../screens/mywallet.md)
