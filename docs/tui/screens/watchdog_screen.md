# Watchdog Monitor

> Continuous monitoring with custom alert conditions on a market.

## Overview

The Watchdog Monitor provides advanced market surveillance with configurable alert conditions. Unlike the basic Watch screen, it supports directional triggers (price above/below a threshold) and change-based alerts, making it suited for setting up specific monitoring rules.

## Access

- **Menu shortcut**: `wd` or `watchdog`
- **Menu path**: Page 2 → Watchdog Monitor

## What It Shows

Continuous monitoring output for a market, with alerts triggered when the selected condition is met. Runs until stopped with `Ctrl+C`.

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Market name to watch
2. Alert condition type:

| Option | Condition |
|--------|-----------|
| `1` | Price goes above threshold |
| `2` | Price goes below threshold |
| `3` | Price changes by a specified amount |
| `4` | Any significant change (default) |

Options 1-3 prompt for an additional threshold/change value.

Press `Ctrl+C` to stop monitoring.

## CLI Command

```bash
# Any significant change
polyterm watchdog -m "bitcoin"

# Price above threshold
polyterm watchdog -m "bitcoin" --above 0.70

# Price below threshold
polyterm watchdog -m "bitcoin" --below 0.40

# Price changes by amount
polyterm watchdog -m "bitcoin" --change 0.05
```

## Data Sources

- Gamma REST API for market data polling
- CLOB API as fallback

## Related Screens

- [Watch](../screens/watch.md)
- [Price Alerts](../screens/alertcenter_screen.md)
