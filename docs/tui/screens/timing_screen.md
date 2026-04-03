# Timing Analysis

> Find optimal times to trade a specific market.

## Overview

The Timing Analysis screen analyzes historical trading patterns for a given market to identify when trading activity and price movements are most favorable. It helps traders decide when to enter or exit positions.

## Access

- **Menu shortcut**: `tm` or `timing`
- **Menu path**: Page 2 → Timing Analysis

## What It Shows

After entering a market name, the screen displays timing-related analytics including volume patterns and price movement windows for the selected market.

## Navigation / Keyboard Shortcuts

The screen prompts for a market name, then runs the analysis. No additional keyboard shortcuts within the screen.

## CLI Command

```bash
polyterm timing "market name"
```

## Data Sources

- Gamma REST API for market data
- CLOB API for historical price/volume data

## Related Screens

- [Volume Profile](../screens/volume_screen.md)
- [Analyze](../screens/analyze_screen.md)
