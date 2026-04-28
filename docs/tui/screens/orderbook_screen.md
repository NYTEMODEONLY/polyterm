# Order Book Analyzer

> Real-time and static order book depth visualization with slippage analysis.

## Overview

The Order Book screen provides two modes: a live WebSocket-fed depth display that updates in real time, and a static one-shot analysis with ASCII depth charts and slippage calculation. The live mode uses the CLOB WebSocket for streaming order book data with automatic REST polling fallback and renders in a fixed live screen so the header/status remain visible.

## Access

- **Menu shortcut**: `13`, `ob`, or `orderbook`
- **Menu path**: Page 1 → Orderbook

## What It Shows

### Mode Selection

1. **Live Order Book** -- real-time WebSocket depth display
2. **Static Analysis** -- one-shot depth chart and slippage calculation

### Live Mode Display

- Bid/ask depth table with proportional bar visualization
- Spread (absolute and percentage), colored by width (green < 1%, yellow < 3%, red >= 3%)
- Mid price
- Bid and ask depth totals
- Imbalance meter showing which side is heavier
- Last trade price with directional arrow and session price tracking
- Connection status indicator (connected, connecting, reconnecting, REST fallback, disconnected)
- Resolution banner when a market settles (colored YES/NO outcome)
- Message count and last update timestamp

### Static Mode Display

- ASCII depth chart
- Slippage calculation for a given order size and side (buy/sell)
- Configurable depth (1-100 levels)

## Navigation / Keyboard Shortcuts

### Live Mode

| Key | Action |
|-----|--------|
| `P` | Pause / resume display updates |
| `D` | Cycle depth levels (10 / 20 / 50) |
| `Q` | Quit live feed |

### Market Selection (both modes)

| Key | Action |
|-----|--------|
| `1` | Choose from active market list |
| `2` | Enter token ID manually |
| `b` | Back to main menu |

For markets with two tokens, a follow-up prompt lets you select YES or NO token.

## CLI Command

```bash
# Live mode
polyterm orderbook <token_id> --live [--refresh 0.5]

# Static mode
polyterm orderbook <token_id> --depth=20 --chart [--slippage=1000 --side=buy]
```

## Data Sources

- CLOB WebSocket (`wss://ws-subscriptions-clob.polymarket.com/ws/market`) for live streaming
- CLOB REST API for static snapshots and REST fallback (5-second polling interval)
- Gamma REST API for market selection list

## Related Screens

- [Predictions](../screens/predictions.md)
- [Fees Calculator](../screens/fees.md)
