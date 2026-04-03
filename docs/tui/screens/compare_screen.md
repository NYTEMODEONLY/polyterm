# Compare Screen

> Compare multiple markets side by side.

## Overview

The Compare screen launches an interactive mode that lets you select up to 4 markets and view them together. It displays sparklines, price changes, volumes, and key metrics for each market, making it easy to spot relative value or potential arbitrage across related markets.

## Access

- **Menu shortcut**: `cmp` or `compare`
- **Menu path**: Type shortcut from either page

## What It Shows

- Side-by-side market data for up to 4 selected markets
- Sparklines showing recent price trends
- Price changes, volumes, and other key metrics
- Combined probability analysis for potential arbitrage detection

## Navigation / Keyboard Shortcuts

- Launches directly into interactive mode
- Market selection is handled within the interactive CLI command
- Returns to menu when the command completes

## CLI Command

```bash
polyterm compare -i
```

## Data Sources

- Gamma REST API (market metadata and pricing)
- Local SQLite database (price history for sparklines)

## Related Screens

- [Chart](../screens/chart_screen.md) - detailed chart for a single market
- [Correlate](../screens/correlate_screen.md) - find markets correlated to a given market
