# P&L Tracker

> Track your profit and loss over configurable time periods.

## Overview

The P&L screen shows a detailed profit-and-loss summary for your tracked positions. You select a time period (today, week, month, year, or all time) and get a breakdown of gains, losses, and net performance. Always runs in detailed mode for maximum insight.

## Access

- **Menu shortcut**: `pnl`
- **Menu path**: Page 2 → P&L

## What It Shows

A time-period selection menu:

1. **Today** -- current day's P&L
2. **Last 7 days** -- weekly summary
3. **Last 30 days** -- monthly summary (default)
4. **Last year** -- yearly summary
5. **All time** -- complete history

The output includes detailed position-by-position P&L data.

## Navigation / Keyboard Shortcuts

Standard numbered menu (`1`-`5`, `b` to go back).

## CLI Command

```bash
polyterm pnl --period <day|week|month|year|all> --detailed
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for tracked positions
- Gamma REST API / Data API for current market prices

## Related Screens

- [Position Tracker](../screens/position_screen.md)
- [Portfolio](../screens/portfolio.md)
- [My Wallet](../screens/mywallet.md)
