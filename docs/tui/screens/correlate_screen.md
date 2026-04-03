# Correlate Screen

> Find markets related to a given market for hedging or doubling exposure.

## Overview

The Correlate screen discovers markets that move together (positively correlated), move inversely, or share time-based relationships with a selected market. This is useful for building hedged positions or finding opportunities to increase exposure to a theme.

## Access

- **Menu shortcut**: `corr` or `correlate`
- **Menu path**: Type shortcut from either page

## What It Shows

- Positively correlated markets
- Inversely correlated markets
- Time-variant related markets
- Correlation strength indicators

## Navigation / Keyboard Shortcuts

- Prompted for a market search term
- Prompted for number of results (default: 10)
- Returns to menu when the command completes

## CLI Command

```bash
polyterm correlate --market <search> --limit <n>
```

## Data Sources

- Gamma REST API (market data and pricing for correlation analysis)

## Related Screens

- [Compare](../screens/compare_screen.md) - view correlated markets side by side
- [Chart](../screens/chart_screen.md) - visualize price history of related markets
