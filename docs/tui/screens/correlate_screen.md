# Correlate Screen

> Find markets related to a given market for hedging or doubling exposure.

## Overview

The Correlate screen discovers markets that move together (positively correlated), move inversely, or share time-based relationships with a selected market. This is useful for building hedged positions or finding opportunities to increase exposure to a theme.

## Access

- **Menu shortcut**: `corr` or `correlate`
- **Menu path**: Type shortcut from either page

## What It Shows

- Positively correlated markets
- Inversely correlated markets
- Time-variant related markets
- Correlation strength indicators

## Navigation / Keyboard Shortcuts

- Prompted for a market search term
- Prompted for number of results (default: 10)
- Returns to menu when the command completes

## CLI Command

```bash
polyterm correlate --market <search> --limit <n>
```

## Data Sources

- Gamma REST API (market data and pricing for correlation analysis)

## Related Screens

- [Compare](../screens/compare_screen.md) - view correlated markets side by side
- [Chart](../screens/chart_screen.md) - visualize price history of related markets

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
