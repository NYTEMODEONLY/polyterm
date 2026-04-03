# Quick Actions Screen

> Fast access to common trading tasks.

## Overview

The Quick Actions screen provides a streamlined menu for common market lookups. After selecting an action type, you enter a market name and the corresponding quick command runs immediately. This is designed for rapid, single-purpose queries without navigating through full-featured screens.

## Access

- **Menu shortcut**: `qk` or `quick`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A numbered menu with five actions:

1. **Quick price check** -- current price for a market
2. **Quick buy calculation** -- cost/return analysis for buying
3. **Quick sell calculation** -- cost/return analysis for selling
4. **Quick market info** -- summary information about a market
5. **Quick add to watchlist** -- add a market to your watchlist

After selecting an action, you are prompted for a market name.

## Navigation / Keyboard Shortcuts

- Enter a number `1`-`5` to select an action
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Price check | `polyterm quick price <market>` |
| Buy calculation | `polyterm quick buy <market>` |
| Sell calculation | `polyterm quick sell <market>` |
| Market info | `polyterm quick info <market>` |
| Add to watchlist | `polyterm quick watch <market>` |

## Data Sources

- Gamma API for market data and pricing
- Local SQLite database for watchlist storage

## Related Screens

- [Quick Trade Screen](../screens/quicktrade_screen.md)
