# Depth Screen

> Analyze order book depth and estimate slippage for a given trade size.

## Overview

The Depth screen shows liquidity at each price level in a market's order book and estimates how much slippage to expect for a specified trade size. This helps traders understand the true cost of entering or exiting a position.

## Access

- **Menu shortcut**: `dp` or `depth`
- **Menu path**: Type shortcut from either page

## What It Shows

- Order book depth at each price level
- Liquidity distribution across bids and asks
- Slippage estimate for the specified trade size

## Navigation / Keyboard Shortcuts

- Prompted for a market search term
- Prompted for trade size in dollars (default: $1000)
- Returns to menu when the command completes

## CLI Command

```bash
polyterm depth --market <search> --size <amount>
```

## Data Sources

- CLOB REST API (order book data)

## Related Screens

- [Order Book](../screens/orderbook_screen.md) - real-time order book with WebSocket feed
- [Fees](../screens/fees_screen.md) - fee and slippage calculator
- [Chart](../screens/chart_screen.md) - price history visualization
