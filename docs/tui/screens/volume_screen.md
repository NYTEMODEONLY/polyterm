# Volume Profile Analysis

> Analyze volume distribution at different price levels for a market.

## Overview

The Volume Profile screen shows how trading volume is distributed across price levels for a given market. This helps identify support/resistance zones where significant trading activity has occurred, which can inform entry and exit decisions.

## Access

- **Menu shortcut**: `vol` or `volume`
- **Menu path**: Page 2 → Volume Profile Analysis

## What It Shows

A volume-at-price profile for the selected market, broken into configurable price level buckets. Higher-volume levels indicate prices where traders have shown the most interest.

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Market name
2. Number of price levels (default: 10)

## CLI Command

```bash
polyterm volume -m "market name" -l 10
```

## Data Sources

- Gamma REST API for market data
- CLOB API for trade history and volume data

## Related Screens

- [Timing Analysis](../screens/timing_screen.md)
- [Market Statistics](../screens/analyze_screen.md)

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
