# Benchmark Screen

> Compare your trading performance to market averages.

## Overview

The Benchmark screen runs a detailed performance comparison between your trading results and market-wide averages for a selected time period. It always runs in detailed mode.

## Access

- **Menu shortcut**: `bench`, `benchmark`
- **Menu path**: Extended shortcuts menu

## What It Shows

Detailed benchmark comparison including your returns vs market averages over the selected period.

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
polyterm benchmark --period PERIOD --detailed
```

Where `PERIOD` is one of: `week`, `month`, `quarter`, `year`, `all`.

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for your trade history
- Gamma / CLOB APIs for market-wide averages

## Related Screens

- [attribution_screen](../screens/attribution_screen.md) -- what drove your performance
- [analyze_screen](../screens/analyze_screen.md) -- portfolio exposure analysis
- [backtest_screen](../screens/backtest_screen.md) -- test strategies on historical data

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
