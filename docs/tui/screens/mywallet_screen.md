# My Wallet Screen

> Connect and track your Polymarket wallet activity (view-only).

## Overview

The My Wallet Screen lets you connect a wallet address and view your Polymarket activity without requiring private keys. It provides access to wallet summary, open positions, trade history, and P&L data. All tracking is strictly view-only.

## Access

- **Menu shortcut**: `mw`, `mywallet`, `wallet`
- **Menu path**: Extended shortcuts menu

## What It Shows

An options menu with seven actions:

1. **Connect/change wallet** -- set or update your wallet address
2. **View wallet summary** -- overview of wallet activity
3. **View positions** -- open positions from on-chain data
4. **View trade history** -- past trades
5. **View P&L summary** -- profit and loss aggregation
6. **Interactive mode** -- full interactive wallet explorer
7. **Disconnect wallet** -- remove stored wallet address

## Navigation / Keyboard Shortcuts

- `1`-`7` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Connect wallet | `polyterm mywallet --connect` |
| Wallet summary | `polyterm mywallet` |
| View positions | `polyterm mywallet -p` |
| Trade history | `polyterm mywallet -h` |
| P&L summary | `polyterm mywallet --pnl` |
| Interactive mode | `polyterm mywallet -i` |
| Disconnect | `polyterm mywallet --disconnect` |

## Data Sources

- Data API (`data-api.polymarket.com`) for wallet positions, activity, and trades
- Config file (`~/.polyterm/config.toml`) for stored wallet address

## Related Screens

- [journal_screen](../screens/journal_screen.md) -- trade journal for documenting trades
- [leaderboard_screen](../screens/leaderboard_screen.md) -- see your ranking among traders
