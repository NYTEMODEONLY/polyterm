# Monitor Screen

> Polling-based market monitoring with category and sub-category filtering.

## Overview

The Monitor Screen provides a guided setup for the market monitor CLI command. It lets you configure the number of markets, category/sub-category filters, refresh rate, and active-only filtering before launching a continuously refreshing market table.

## Access

- **Menu shortcut**: `1`, `mon`
- **Menu path**: Page 1 -> Monitor

## What It Shows

An interactive configuration flow:

1. **Market count** -- how many markets to display (default: 20)
2. **Category selection** -- All Markets, Sports, Crypto, or Politics
3. **Sub-category** -- drill-down options per category (e.g., Sports -> NFL/NBA/MLB/NHL/Soccer/Golf/Tennis/UFC/F1)
4. **Refresh rate** -- seconds between updates (default: 5)
5. **Active only** -- whether to filter to active markets only (default: yes)

After configuration, the monitor runs continuously until stopped with `Ctrl+C`.

## Navigation / Keyboard Shortcuts

- Numbered selections for category and sub-category
- `Ctrl+C` to stop the monitor

## CLI Command

```bash
polyterm monitor --limit <n> --refresh <sec> [--category <cat>] [--active-only]
```

## Data Sources

- Gamma REST API (market listings, prices, volumes)

## Related Screens

- [live_monitor](../screens/live_monitor.md) -- WebSocket-based real-time monitoring
- [liquidity_screen](../screens/liquidity_screen.md) -- liquidity comparison across markets
