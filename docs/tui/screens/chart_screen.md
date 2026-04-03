# Chart Screen

> View ASCII price history charts for any market.

## Overview

The Chart screen generates terminal-based price visualizations for a given market. It supports both full line charts and compact sparkline views, with a configurable time window for the historical data displayed.

## Access

- **Menu shortcut**: `ch` or `chart`
- **Menu path**: Type shortcut from either page

## What It Shows

- ASCII line chart of price movement over time (using Bresenham's algorithm)
- Sparkline view as a compact alternative (8-level block characters)
- Customizable timeframe in hours

## Navigation / Keyboard Shortcuts

- Prompted for market ID or search term
- Prompted for hours of history (default: 24)
- Prompted for view type: `chart` or `sparkline`
- Returns to menu when the command completes

## CLI Command

```bash
polyterm chart -m <market> -h <hours>
polyterm chart -m <market> -h <hours> --sparkline
```

## Data Sources

- CLOB `/prices-history` endpoint for real market price data
- Falls back to local SQLite database snapshots if CLOB data is unavailable

## Related Screens

- [Compare](../screens/compare_screen.md) - compare charts across multiple markets
- [Stats](../screens/stats_screen.md) - numerical statistics for the same market data
- [Depth](../screens/depth_screen.md) - current order book depth analysis
