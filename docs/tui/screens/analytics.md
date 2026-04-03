# Analytics Screen

> Market-level analytics including trending markets by volume.

## Overview

The Analytics screen provides market-wide insights. Its primary feature is a trending markets table ranked by 24-hour trading volume. Unlike most TUI screens, the trending markets view fetches and renders data directly via the API aggregator rather than invoking a CLI subprocess. Market correlations, price predictions, and volume analysis options are listed but not yet implemented.

## Access

- **Menu shortcut**: `5`, `a`
- **Menu path**: Page 1 item 5 (Analytics)

## What It Shows

A submenu with four analytics types:

1. **Trending Markets** -- table of top markets by 24hr volume showing rank, market name, probability, volume, and time until end
2. **Market Correlations** -- (coming soon)
3. **Price Predictions** -- (coming soon)
4. **Volume Analysis** -- (coming soon)

The trending markets table columns:
- `#` -- rank
- `Market` -- question text (max 50 chars)
- `Probability` -- YES price as percentage, color-coded
- `24hr Volume` -- formatted as $K or $M
- `Ends` -- countdown (hours/days/weeks/months)

## Navigation / Keyboard Shortcuts

- `1`-`4` to select an analytics type
- `b` to return to the main menu
- For trending markets, you can set the number of results (1-50, default 10)

## CLI Command

This screen does **not** invoke a CLI subprocess. It calls `APIAggregator.get_top_markets_by_volume()` directly and renders a Rich table in-process.

## Data Sources

- Gamma REST API (primary, via `APIAggregator`)
- CLOB REST API (fallback)

## Related Screens

- [analyze_screen](../screens/analyze_screen.md) -- portfolio-level analytics
- [arbitrage](../screens/arbitrage.md) -- arbitrage opportunity scanning
