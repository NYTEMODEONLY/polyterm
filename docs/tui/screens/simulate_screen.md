# Simulate Screen

> Calculate potential profit/loss before trading.

## Overview

The Simulate screen launches the interactive position simulator. It helps users understand potential outcomes of a trade including profit/loss at various exit prices, ROI calculations, and fee impact -- all without placing an actual trade.

## Access

- **Menu shortcut**: `sim`, `simulate`
- **Menu path**: Page 2 (Simulate)

## What It Shows

An introductory panel explaining the simulator's capabilities:

- How much you could win or lose
- Potential ROI
- Outcomes at different exit prices
- Fee impact on returns

Then launches the interactive CLI which prompts for trade parameters.

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. Interaction is handled by the interactive CLI subprocess.

## CLI Command

```bash
polyterm simulate -i
```

## Data Sources

- User input (entry price, position size, exit scenarios)
- Fee calculations (2% taker fee on winnings)

## Related Screens

- [size_screen](../screens/size_screen.md) -- Kelly Criterion position sizing
- [spread_screen](../screens/spread_screen.md) -- spread and execution cost analysis
