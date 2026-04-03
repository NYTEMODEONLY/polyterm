# Leaderboard Screen

> View top traders ranked by profit, volume, win rate, or activity.

## Overview

The Leaderboard Screen shows trader rankings across Polymarket. You can view leaderboards sorted by different metrics and filtered by time period, or check your own ranking if you have a connected wallet.

## Access

- **Menu shortcut**: `lb`, `leaderboard`
- **Menu path**: Extended shortcuts menu

## What It Shows

A two-step selection flow:

1. **Leaderboard type** -- Top by Profit, Volume, Win Rate, Most Active, or My Ranking
2. **Time period** (except for My Ranking) -- 24 hours, 7 days, 30 days, or All time

## Navigation / Keyboard Shortcuts

- `1`-`5` to select leaderboard type
- `1`-`4` to select time period
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Top by profit (7d) | `polyterm leaderboard -t profit -p 7d` |
| Top by volume (24h) | `polyterm leaderboard -t volume -p 24h` |
| Top by win rate (30d) | `polyterm leaderboard -t winrate -p 30d` |
| Most active (all time) | `polyterm leaderboard -t active -p all` |
| My ranking | `polyterm leaderboard --me` |

## Data Sources

- Polymarket API (trader statistics)

## Related Screens

- [mywallet_screen](../screens/mywallet_screen.md) -- view your own wallet and P&L
