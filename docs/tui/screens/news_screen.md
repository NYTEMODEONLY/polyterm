# News Screen

> Latest headlines from crypto and prediction market news sources.

## Overview

The News Screen aggregates RSS headlines from The Block, CoinDesk, and Decrypt. It supports viewing recent news, breaking news within a shorter time window, or news matched to a specific market by keyword.

## Access

- **Menu shortcut**: `nw`, `news`
- **Menu path**: Extended shortcuts menu

## What It Shows

An options menu with three modes:

1. **Latest news (24h)** -- headlines from the past 24 hours
2. **Breaking news (6h)** -- headlines from the past 6 hours only
3. **News for a market** -- prompts for a search term and shows matching articles

## Navigation / Keyboard Shortcuts

- `1`-`3` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Latest news | `polyterm news` |
| Breaking news | `polyterm news --hours 6` |
| Market-specific | `polyterm news --market <term>` |

## Data Sources

- RSS feeds (The Block, CoinDesk, Decrypt)
- 5-minute cache to reduce repeated fetches

## Related Screens

- [monitor](../screens/monitor.md) -- market monitoring for price changes alongside news
