# Benchmark Screen

> Compare your trading performance to market averages.

## Overview

The Benchmark screen runs a detailed performance comparison between your trading results and market-wide averages for a selected time period. It always runs in detailed mode.

## Access

- **Menu shortcut**: `bench`, `benchmark`
- **Menu path**: Extended shortcuts menu

## What It Shows

Detailed benchmark comparison including your returns vs market averages over the selected period.

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
polyterm benchmark --period PERIOD --detailed
```

Where `PERIOD` is one of: `week`, `month`, `quarter`, `year`, `all`.

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for your trade history
- Gamma / CLOB APIs for market-wide averages

## Related Screens

- [attribution_screen](../screens/attribution_screen.md) -- what drove your performance
- [analyze_screen](../screens/analyze_screen.md) -- portfolio exposure analysis
- [backtest_screen](../screens/backtest_screen.md) -- test strategies on historical data
