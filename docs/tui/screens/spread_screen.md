# Spread Screen

> Understand bid/ask spread and execution costs for a market.

## Overview

The Spread screen analyzes the bid/ask spread and estimated execution costs for a given market at a specified trade amount. This helps users understand the true cost of entering or exiting a position, beyond just the displayed price.

## Access

- **Menu shortcut**: `sp`, `spread`
- **Menu path**: Page 2 (Spread)

## What It Shows

After prompting for a market name and trade amount, it displays:

- Current bid/ask spread
- Spread percentage
- Estimated slippage at the specified trade size
- Execution cost analysis

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. The user enters a market name and trade amount at the prompts; leaving the market name empty returns to the menu.

## CLI Command

```bash
polyterm spread "<market>" --amount <USD>
```

Default trade amount is `100` USD.

## Data Sources

- CLOB API (order book data for spread calculation)

## Related Screens

- [size_screen](../screens/size_screen.md) -- position sizing calculator
- [simulate_screen](../screens/simulate_screen.md) -- P&L simulation with fee impact
