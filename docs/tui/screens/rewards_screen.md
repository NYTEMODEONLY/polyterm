# Rewards Screen

> Estimate your Polymarket holding and liquidity rewards.

## Overview

The Rewards screen estimates your holding rewards based on Polymarket's 4% APY program. Qualifying positions must be in the 20-80 cent price range and held for at least 24 hours. The screen shows daily, weekly, monthly, and yearly reward projections along with liquidity provision eligibility.

## Access

- **Menu shortcut**: `rw` or `rewards`
- **Menu path**: Page 2 -> (shortcut-only, not a numbered item)

## What It Shows

A menu with two options:

1. **View reward estimates** -- shows projected rewards for qualifying positions
2. **JSON output** -- same data in JSON format for programmatic use

Reward output includes per-position eligibility, estimated APY earnings, and total projections across time horizons.

## Navigation / Keyboard Shortcuts

- Enter `1` for standard output, `2` for JSON
- Enter `b` to return to the main menu
- `Ctrl+C` returns to the menu

## CLI Commands

| Option | Command |
|--------|---------|
| Standard view | `polyterm rewards` |
| JSON output | `polyterm rewards --format json` |

## Data Sources

- Data API (`data-api.polymarket.com`) for wallet positions
- Gamma API for current market prices
- Local config (`~/.polyterm/config.toml`) for wallet address

## Related Screens

- [Portfolio](../screens/export.md)
