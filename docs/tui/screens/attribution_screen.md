# Attribution Screen

> Analyze what is driving your trading performance over a selected time period.

## Overview

The Attribution screen breaks down trading performance by identifying which factors (market categories, trade types, timing, etc.) contributed to gains or losses. You select a time period and the CLI command produces the attribution analysis.

## Access

- **Menu shortcut**: `attr`, `attribution`
- **Menu path**: Extended shortcuts menu

## What It Shows

Performance attribution analysis for the selected period, showing which factors drove returns.

## Navigation / Keyboard Shortcuts

Time period selection:

- `1` -- Last week
- `2` -- Last month (default)
- `3` -- Last quarter
- `4` -- Last year
- `5` -- All time
- `b` -- Back to menu

## CLI Command

```
polyterm attribution --period PERIOD
```

Where `PERIOD` is one of: `week`, `month`, `quarter`, `year`, `all`.

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for trade history

## Related Screens

- [analyze_screen](../screens/analyze_screen.md) -- portfolio exposure analysis
- [benchmark_screen](../screens/benchmark_screen.md) -- compare performance to market averages
