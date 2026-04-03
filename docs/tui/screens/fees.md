# Fee & Slippage Calculator

> Calculate the true cost of trades including fees and slippage.

## Overview

The Fees screen launches an interactive calculator that breaks down trading costs on Polymarket. It covers the taker fee structure (0% maker, 2% taker on winnings), estimates slippage from order book depth, projects net profit/loss, and includes Polygon network gas fee estimates.

## Access

- **Menu shortcut**: `fee` or `fees`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

An interactive calculator that computes:

- Polymarket fee breakdown (2% taker fee on winnings)
- Slippage estimation based on order book depth
- Net profit/loss projections after all costs
- Gas fee estimates for Polygon network transactions

## Navigation / Keyboard Shortcuts

No special keyboard shortcuts. This is an interactive prompt-based calculator.

## CLI Command

```bash
polyterm fees -i
```

## Data Sources

- CLOB API for order book data (slippage estimation)
- Hardcoded Polymarket fee structure (2% taker on winnings)
- Polygon network gas estimates

## Related Screens

- [Exit Strategy](../screens/exit.md) -- factor fees into exit targets
- [Hot Markets](../screens/hot.md) -- check costs on active markets
