# Watch Specific Market

> Monitor a single market with configurable alert thresholds.

## Overview

The Watch screen lets you track a specific market in real time, alerting you when the probability changes by more than a configurable threshold. It accepts either a market search term or a direct Market ID, and runs continuously until stopped.

## Access

- **Menu shortcut**: `4`
- **Menu path**: Page 1 → Watch (option 4)

## What It Shows

A live updating view of a single market's probability, refreshing at a configurable interval. Alerts are triggered when the probability change exceeds the threshold.

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Market search term or Market ID
2. Alert threshold for probability change (default: 5%)
3. Check interval in seconds (default: 10)

Press `Ctrl+C` to stop watching and return to the menu.

## CLI Command

```bash
polyterm watch --market <market_id> --threshold 5 --interval 10
```

## Data Sources

- Gamma REST API for market data polling
- CLOB API as fallback

## Related Screens

- [Watchdog Monitor](../screens/watchdog_screen.md)
- [Live Monitor](../screens/alerts_screen.md)
- [Price Alerts](../screens/alertcenter_screen.md)
