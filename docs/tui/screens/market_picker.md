# Market Picker

> Reusable component for selecting markets from a numbered list.

## Overview

The Market Picker is an internal TUI component used by other screens that need the user to select a market. It fetches active markets from the Gamma API, displays them in a numbered table with price and volume, and returns the selected market dictionary. It is not a standalone screen accessible from the menu.

## Access

- **Menu shortcut**: None (internal component)
- **Menu path**: Not directly accessible; used by other screens

## What It Shows

A table of active markets with columns:

- **#** -- selection number
- **Market** -- market title (truncated to 50 chars)
- **Price** -- YES price as a percentage
- **Volume** -- 24-hour volume (formatted as $K/$M)

Below the table, the user can enter a number to select, `m` for manual market ID entry, or `q` to cancel.

## Key Functions

| Function | Purpose |
|----------|---------|
| `fetch_markets(limit)` | Fetches active markets from Gamma API |
| `display_market_list(console, markets)` | Renders the numbered market table |
| `pick_market(console, prompt, allow_manual, limit)` | Full interactive picker flow |
| `get_market_id(market)` | Extracts market ID from a market dict |
| `get_market_title(market)` | Extracts market title from a market dict |

## Data Sources

- Gamma REST API (`GammaClient.get_markets()`)

## Related Screens

- [live_monitor](../screens/live_monitor.md) -- uses its own market search (not this picker)
- [monitor](../screens/monitor.md) -- category-based market selection
