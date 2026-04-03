# NegRisk Screen

> Scan multi-outcome markets for guaranteed-profit arbitrage opportunities.

## Overview

The NegRisk Screen scans multi-outcome (NegRisk) markets for arbitrage opportunities. When the sum of all YES prices in a multi-outcome market is less than $1.00, buying all outcomes guarantees a profit. The screen offers a default scan or a custom minimum spread setting.

## Access

- **Menu shortcut**: `nr`, `negrisk`
- **Menu path**: Extended shortcuts menu

## What It Shows

An options menu with two modes:

1. **Scan with default settings** -- uses the default minimum spread
2. **Custom minimum spread** -- prompts for a spread value (e.g., 0.03)

## Navigation / Keyboard Shortcuts

- `1`-`2` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Default scan | `polyterm negrisk` |
| Custom spread | `polyterm negrisk --min-spread <value>` |

## Data Sources

- Gamma REST API (multi-outcome market listings)
- CLOB API (outcome prices)

## Related Screens

- [liquidity_screen](../screens/liquidity_screen.md) -- compare market liquidity and spreads
