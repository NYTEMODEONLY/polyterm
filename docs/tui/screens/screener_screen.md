# Market Screener Screen

> Filter markets by multiple criteria.

## Overview

The Market Screener screen provides a way to scan for markets matching specific conditions. It offers both a full interactive mode and quick-scan presets for common queries like high-volume markets, big movers, and markets ending soon.

## Access

- **Menu shortcut**: `scr` or `screener`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A menu with four options:

1. **Interactive mode** -- full filter builder with prompts for volume, price range, category, and more
2. **Quick scan: high volume** -- markets with volume above $10,000, sorted by volume
3. **Quick scan: big movers** -- markets with price change above 5%, sorted by change
4. **Quick scan: ending soon** -- markets resolving within 7 days, sorted by end date

## Navigation / Keyboard Shortcuts

- Enter a number `1`-`4` to select a scan type
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Interactive | `polyterm screener -i` |
| High volume | `polyterm screener -v 10000 -s volume` |
| Big movers | `polyterm screener --min-change 5 -s change` |
| Ending soon | `polyterm screener --ending-within 7 -s end_date` |

## Data Sources

- Gamma API for market listings, volume, and pricing data

## Related Screens

- [Presets Screen](../screens/presets_screen.md)
- [Calendar Screen](../screens/calendar_screen.md)
