# Market History

> View price and volume history for any market.

## Overview

The History screen lets you look up historical price and volume data for a specific market over configurable time periods. It displays the data as a chart in the terminal. You enter a market name or ID and select a time range, then the screen renders a visual history.

## Access

- **Menu shortcut**: `hist` or `history`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A two-step prompt flow:

1. **Market selection** -- enter a market name or ID
2. **Time period** -- choose from:
   - Last day
   - Last week (default)
   - Last month
   - All time

The result is an ASCII chart showing price history for the selected period.

## Navigation / Keyboard Shortcuts

- `1`-`4` -- Select time period
- No additional keyboard shortcuts; prompt-based flow

## CLI Command

```bash
polyterm history <market> --period week --chart
polyterm history <market> --period day --chart
polyterm history <market> --period month --chart
polyterm history <market> --period all --chart
```

## Data Sources

- CLOB API price history endpoint (`/prices-history`)
- Falls back to local SQLite database snapshots if CLOB data is unavailable

## Related Screens

- [Export](../screens/export.md) -- export the historical data to a file
- [Hot Markets](../screens/hot.md) -- find markets with significant recent movement
