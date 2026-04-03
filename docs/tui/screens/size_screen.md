# Size Screen

> Calculate optimal bet sizes using Kelly Criterion.

## Overview

The Size screen launches the interactive position size calculator. It uses the Kelly Criterion to determine optimal bet sizing based on the user's bankroll, probability estimate, and current market price. It provides full Kelly, fractional Kelly, and fixed percentage alternatives.

## Access

- **Menu shortcut**: `sz`, `size`
- **Menu path**: Page 2 (Size)

## What It Shows

An introductory panel, then launches the interactive CLI which calculates:

- Edge and expected value per dollar
- Full Kelly recommended size
- Fractional Kelly sizes (quarter, half)
- Fixed percentage alternatives (1%, 2%, 5%)
- Outcome projections (profit if win, loss if lose)

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. Interaction is handled by the interactive CLI subprocess.

## CLI Command

```bash
polyterm size -i
```

## Data Sources

- User input (bankroll, probability estimate, market price)

## Related Screens

- [simulate_screen](../screens/simulate_screen.md) -- P&L calculator for trade scenarios
- [spread_screen](../screens/spread_screen.md) -- execution cost analysis
