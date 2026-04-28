# Live Monitor Screen

> Real-time market monitoring with WebSocket-powered price updates.

## Overview

The Live Monitor Screen provides an interactive setup flow for launching a real-time market monitor. It supports monitoring a specific market, a category of markets, or all active markets. The monitor launches in a new terminal window (with a fallback to the current terminal) and uses a fixed live dashboard while trades stream.

## Access

- **Menu shortcut**: `2`, `l`
- **Menu path**: Page 1 -> Live Monitor

## What It Shows

A three-step setup flow:

1. **Monitoring mode** -- choose between:
   - Monitor a specific market (search by ID, slug, or keyword)
   - Monitor a category (sports, crypto, politics with sub-categories)
   - Monitor all active markets
2. **Market/category selection** -- depending on mode, search for a market or drill into sub-categories (e.g., Sports -> NFL, Crypto -> Bitcoin)
3. **Launch** -- opens a live monitor in a new terminal window

For category mode, the screen verifies that markets exist for the selected category before launching.

The launched monitor keeps its header, connection state, trade counters, buy/sell totals, last trade time, recent trades table, and status footer visible while RTDS messages arrive.

## Navigation / Keyboard Shortcuts

- `1`-`3` to select monitoring mode
- Numbered selections for search results and sub-categories
- `Ctrl+C` to cancel setup or stop the monitor

## CLI Command

```bash
polyterm live-monitor [--market <id>] [--category <category>]
```

The screen constructs and runs the `LiveMarketMonitor` class directly, either in a new terminal window or the current terminal as fallback.

## Data Sources

- Gamma REST API (market search, category verification)
- RTDS WebSocket (`wss://ws-live-data.polymarket.com`) for real-time price updates
- Polling fallback when WebSocket is unavailable

## Related Screens

- [monitor](../screens/monitor.md) -- polling-based market monitor with category filters
- [market_picker](../screens/market_picker.md) -- reusable market selection component
