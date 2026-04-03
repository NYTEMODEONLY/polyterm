# Signal-Based Predictions

> Algorithmic multi-signal predictions using momentum, volume, whale, and technical indicators.

## Overview

The Predictions screen generates directional predictions for Polymarket markets using five signal types: momentum, volume acceleration, whale positioning, smart money activity, and RSI-based technicals. All analysis is algorithmic with no external APIs or LLMs. You can analyze top markets by volume, pick a specific market, or enter a market ID manually.

## Access

- **Menu shortcut**: `10` or `pred`
- **Menu path**: Page 1 → Predictions

## What It Shows

### Market Selection

1. **Analyze Top Markets** -- run predictions on the highest-volume markets (configurable limit, 1-25)
2. **Select Specific Market** -- choose from an interactive market list
3. **Enter Market ID** -- manual ID or slug entry

### Prediction Settings

After market selection, you configure:

- **Prediction horizon** -- how far ahead to predict (1-168 hours, default 24)
- **Minimum confidence** -- filter threshold for signal strength (0-1, default 0.5)

### Output

For each market: directional signal (bullish/bearish/neutral), confidence score, and breakdown by individual signal type.

## Navigation / Keyboard Shortcuts

Standard menu selection (`1`-`3`, `b` to go back). Ctrl+C to cancel a running prediction.

## CLI Command

```bash
# Top markets
polyterm predict --limit=10 --horizon=24 --min-confidence=0.5

# Specific market
polyterm predict --market=<id> --horizon=24 --min-confidence=0.5
```

## Data Sources

- Gamma REST API for market data and price history
- Local SQLite database (`~/.polyterm/data.db`) for historical snapshots
- CLOB API for recent price data

## Related Screens

- [Order Book](../screens/orderbook_screen.md)
- [Market Statistics](../screens/stats.md)
- [Arbitrage Scanner](../screens/arbitrage.md)
