# Hot Markets

> See the biggest market movers right now.

## Overview

The Hot Markets screen shows which prediction markets are experiencing the most price movement or volume activity. You can filter to see all movers, only gainers, only losers, or sort by highest volume. Useful for spotting trending markets and potential trading opportunities.

## Access

- **Menu shortcut**: `hot`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A menu with four view options:

1. **Top movers (all)** -- markets with the largest price changes in either direction
2. **Gainers only** -- markets with the biggest price increases
3. **Losers only** -- markets with the biggest price drops
4. **Highest volume** -- markets ranked by trading volume

## Navigation / Keyboard Shortcuts

- `1` -- Top movers (all)
- `2` -- Gainers only
- `3` -- Losers only
- `4` -- Highest volume
- `b` -- Back to main menu

## CLI Command

```bash
polyterm hot              # Top movers (all)
polyterm hot --gainers    # Gainers only
polyterm hot --losers     # Losers only
polyterm hot --volume     # Highest volume
```

## Data Sources

- Gamma REST API for market data and price changes
- CLOB API as fallback (via APIAggregator)

## Related Screens

- [History](../screens/history.md) -- dig into price history of a hot market
- [Fees](../screens/fees.md) -- calculate costs before trading a hot market
