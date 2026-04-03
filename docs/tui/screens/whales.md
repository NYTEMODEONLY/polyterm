# Whale Tracker

> Monitor high-volume trading activity across Polymarket.

## Overview

The Whales screen detects and displays large trades and high-volume activity on Polymarket. It helps identify whale movements that may signal informed trading or market-moving positions. Configurable by minimum amount, lookback period, and result count.

## Access

- **Menu shortcut**: `3` or `w`
- **Menu path**: Page 1 → Whales (option 3)

## What It Shows

A list of high-volume trades and whale activity, filtered by configurable parameters:

- Minimum 24-hour volume threshold
- Lookback period in hours
- Maximum number of results

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Minimum 24hr volume (default: $10,000)
2. Lookback period in hours (default: 24)
3. Maximum results to show (default: 20)

Press `Ctrl+C` to stop and return to the menu.

## CLI Command

```bash
polyterm whales --min-amount 10000 --hours 24 --limit 20
```

## Data Sources

- Gamma REST API for market and trade data
- CLOB WebSocket for real-time trade feeds (when available)
- REST polling fallback via `whale_tracker._run_rest_polling()`

## Related Screens

- [Wallet Tracker](../screens/wallets.md)
- [Copy Trading / Follow](../screens/export.md)
- [Clusters](../screens/alertcenter_screen.md)
