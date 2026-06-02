# Attribution Screen

> Analyze what is driving your trading performance over a selected time period.

## Overview

The Attribution screen breaks down trading performance by identifying which factors (market categories, trade types, timing, etc.) contributed to gains or losses. You select a time period and the CLI command produces the attribution analysis.

## Access

- **Menu shortcut**: `attr`, `attribution`
- **Menu path**: Extended shortcuts menu

## What It Shows

Performance attribution analysis for the selected period, showing which factors drove returns.

## Navigation / Keyboard Shortcuts

Time period selection:

- `1` -- Last week
- `2` -- Last month (default)
- `3` -- Last quarter
- `4` -- Last year
- `5` -- All time
- `b` -- Back to menu

## CLI Command

```
polyterm attribution --period PERIOD
```

Where `PERIOD` is one of: `week`, `month`, `quarter`, `year`, `all`.

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for trade history

## Related Screens

- [analyze_screen](../screens/analyze_screen.md) -- portfolio exposure analysis
- [benchmark_screen](../screens/benchmark_screen.md) -- compare performance to market averages

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
