# Backtest Screen

> Test trading strategies against historical market data.

## Overview

The Backtest screen lets you run strategy backtests either interactively or as quick tests with predefined strategies. Quick tests run each strategy over a 30-day period. Interactive mode allows full customization of strategy parameters.

## Access

- **Menu shortcut**: `bt`, `backtest`
- **Menu path**: Extended shortcuts menu

## What It Shows

Backtest results for the selected strategy, including simulated trade outcomes over the chosen period.

## Navigation / Keyboard Shortcuts

Strategy selection:

- `1` -- Interactive mode (recommended, default)
- `2` -- Quick test: Momentum strategy (30d)
- `3` -- Quick test: Mean Reversion strategy (30d)
- `4` -- Quick test: Whale Follow strategy (30d)
- `5` -- Quick test: Contrarian strategy (30d)
- `b` -- Back to menu

## CLI Commands

| Option | Command |
|--------|---------|
| Interactive | `polyterm backtest -i` |
| Momentum | `polyterm backtest -s momentum -p 30d` |
| Mean Reversion | `polyterm backtest -s mean-reversion -p 30d` |
| Whale Follow | `polyterm backtest -s whale-follow -p 30d` |
| Contrarian | `polyterm backtest -s contrarian -p 30d` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for historical snapshots
- Gamma / CLOB APIs for market data

## Related Screens

- [benchmark_screen](../screens/benchmark_screen.md) -- compare performance to market averages
- [attribution_screen](../screens/attribution_screen.md) -- analyze performance drivers

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
