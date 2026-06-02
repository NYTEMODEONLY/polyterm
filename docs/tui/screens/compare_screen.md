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

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm the linked source file still exists and the module name has not changed.
- Update command examples, TUI shortcuts, and option names when Click or controller routing changes.
- Keep data-source notes current with the active Polymarket API contracts.
- Prefer concrete endpoint names, identifier types, and output fields over broad marketing language.
- Run `./test_all_commands.sh` when a CLI command or shortcut is affected.
- Run `.venv/bin/python scripts/validate_docs.py` before committing documentation changes.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Examples should be copy-pasteable from the repository root unless stated otherwise.
- Pages for view-only workflows should say so when wallet or trading context is involved.
- Pages that depend on live market data should name Gamma, Data API, or CLOB as the source.
- Alias pages should point to the canonical page and explain why the alias exists.
- New modules should have a dedicated page rather than relying only on the index.
