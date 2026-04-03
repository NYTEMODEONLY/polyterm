# Arbitrage Screen

> Scan for arbitrage opportunities across Polymarket and optionally Kalshi.

## Overview

The Arbitrage screen scans for pricing inefficiencies where buying both sides of a market costs less than the guaranteed payout. It prompts for scan parameters (minimum spread, result limit, cross-platform inclusion) then invokes the CLI arbitrage scanner.

## Access

- **Menu shortcut**: `9`, `arb`
- **Menu path**: Page 1 item 9 (Arbitrage)

## What It Shows

After configuring scan parameters, displays arbitrage opportunities including:

- Intra-market opportunities (YES + NO < $0.975)
- Correlated market divergences
- Cross-platform Polymarket vs Kalshi spreads (optional)

## Navigation / Keyboard Shortcuts

Interactive prompts before scan:

1. **Minimum spread %** -- default 2.5%
2. **Max opportunities** -- default 10, max 50
3. **Include Kalshi** -- y/n, default n

## CLI Command

```
polyterm arbitrage --min-spread=SPREAD --limit=N [--include-kalshi]
```

The spread value entered as a percentage is converted to decimal (e.g., 2.5 becomes 0.025).

## Data Sources

- Gamma REST API (market prices)
- CLOB REST API (fallback)
- Kalshi API (if cross-platform enabled)
- Optional: live WebSocket mid-prices via `OrderBookAnalyzer`

## Related Screens

- [analytics](../screens/analytics.md) -- market analytics and trending
