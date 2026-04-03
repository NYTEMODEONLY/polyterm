# Search Screen

> Advanced market search with filters for volume, price, liquidity, and more.

## Overview

The Search screen launches the interactive market search tool, allowing users to find markets using advanced filters. It provides a streamlined entry point to the `search -i` CLI command from within the TUI.

## Access

- **Menu shortcut**: `sr`, `search`
- **Menu path**: Page 2 (Search)

## What It Shows

A header panel describing the search tool, then launches the interactive search CLI which supports filtering by:

- Category
- Volume and liquidity thresholds
- Price range
- Resolution date (ending soon)
- Multiple sort options (volume, liquidity, price, recent)

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. Interaction is handled by the interactive CLI subprocess.

## CLI Command

```bash
polyterm search -i
```

## Data Sources

- Gamma REST API (market listings and metadata)

## Related Screens

- [stats_screen](../screens/stats_screen.md) -- detailed statistics for a specific market
- [similar_screen](../screens/similar_screen.md) -- find markets related to a given market
