# Volume Profile Analysis

> Analyze volume distribution at different price levels for a market.

## Overview

The Volume Profile screen shows how trading volume is distributed across price levels for a given market. This helps identify support/resistance zones where significant trading activity has occurred, which can inform entry and exit decisions.

## Access

- **Menu shortcut**: `vol` or `volume`
- **Menu path**: Page 2 → Volume Profile Analysis

## What It Shows

A volume-at-price profile for the selected market, broken into configurable price level buckets. Higher-volume levels indicate prices where traders have shown the most interest.

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Market name
2. Number of price levels (default: 10)

## CLI Command

```bash
polyterm volume -m "market name" -l 10
```

## Data Sources

- Gamma REST API for market data
- CLOB API for trade history and volume data

## Related Screens

- [Timing Analysis](../screens/timing_screen.md)
- [Market Statistics](../screens/analyze_screen.md)
