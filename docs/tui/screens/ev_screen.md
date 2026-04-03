# EV Screen

> Calculate whether a trade has positive expected value.

## Overview

The EV (Expected Value) screen helps determine if a bet is mathematically favorable by comparing your estimated probability of an outcome against the market price. It offers both a guided interactive mode and a quick calculation mode for direct input.

## Access

- **Menu shortcut**: `ev`
- **Menu path**: Type shortcut from either page

## What It Shows

- Expected value per dollar wagered
- Edge calculation (your probability vs. market implied probability)
- Whether the trade is +EV or -EV

## Navigation / Keyboard Shortcuts

- **1** - Interactive mode (recommended; guided step-by-step)
- **2** - Quick calculation (provide market name and your probability directly)
- **b** - Back to menu

## CLI Command

```bash
polyterm ev -i                        # Interactive mode
polyterm ev -m <market> -p <probability>  # Quick calculation
```

## Data Sources

- Gamma REST API (current market prices for implied probability)

## Related Screens

- [Predictions](../screens/predictions_screen.md) - signal-based prediction analysis
- [Size](../screens/size_screen.md) - Kelly Criterion position sizing
- [Simulate](../screens/simulate_screen.md) - P&L calculator
