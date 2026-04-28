# Parlay Calculator

> Combine multiple bets into a parlay for higher potential payouts.

## Overview

The Parlay screen calculates combined probability, odds, and expected payout for multi-leg parlay bets. All legs must win for the parlay to pay out. Supports 2-10 legs and includes a generic CLOB V2 protocol fee estimate.

## Access

- **Menu shortcut**: `16`, `parlay`
- **Menu path**: Page 1 → Parlay Calculator

## What It Shows

Two modes of operation:

1. **Interactive mode** -- guided step-by-step parlay builder (recommended)
2. **Quick calculation** -- enter comma-separated probabilities and a bet amount for immediate results

The output includes combined probability, decimal and American odds, expected value, risk level, and fee-adjusted payouts.

## Navigation / Keyboard Shortcuts

Standard menu selection (`1`, `2`, `q` to quit). Probabilities can be entered as decimals (0.65) or percentages (65) -- values above 1 are auto-converted.

## CLI Commands

| Option | CLI command |
|--------|-------------|
| Interactive | `polyterm parlay -i` |
| Quick calc | `polyterm parlay --markets <probs> --amount <amount>` |

Example:

```bash
polyterm parlay --markets 0.65,0.70,0.80 --amount 100
```

## Data Sources

- Pure calculation (no API calls needed for quick mode)
- Gamma REST API when interactive mode looks up live market prices

## Related Screens

- [Odds Converter](../screens/odds_screen.md)
- [Fees Calculator](../screens/fees.md)
- [Position Tracker](../screens/position_screen.md)
