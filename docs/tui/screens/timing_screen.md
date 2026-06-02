# Timing Analysis

> Find optimal times to trade a specific market.

## Overview

The Timing Analysis screen analyzes historical trading patterns for a given market to identify when trading activity and price movements are most favorable. It helps traders decide when to enter or exit positions.

## Access

- **Menu shortcut**: `tm` or `timing`
- **Menu path**: Page 2 → Timing Analysis

## What It Shows

After entering a market name, the screen displays timing-related analytics including volume patterns and price movement windows for the selected market.

## Navigation / Keyboard Shortcuts

The screen prompts for a market name, then runs the analysis. No additional keyboard shortcuts within the screen.

## CLI Command

```bash
polyterm timing "market name"
```

## Data Sources

- Gamma REST API for market data
- CLOB API for historical price/volume data

## Related Screens

- [Volume Profile](../screens/volume_screen.md)
- [Analyze](../screens/analyze_screen.md)

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
