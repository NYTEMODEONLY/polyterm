# Backtest Screen

> DEMO strategy simulation. Not historical backtesting.

## Overview

The Backtest screen launches a seeded random DEMO simulation. It does not replay historical Polymarket trades or prices. The screen shows that disclosure before any run and always passes `--demo` to the CLI.

Do not treat Sharpe, win rate, or P&L from this screen as historical performance.

This workflow is view-only.

## Access

- **Menu shortcut**: `bt`, `backtest`
- **Menu path**: Extended shortcuts menu

## What It Shows

A DEMO disclosure, then simulated random trade outcomes for the selected strategy name. Strategy names only change the RNG heuristic.

## Navigation / Keyboard Shortcuts

Strategy selection:

- `1` -- Interactive DEMO
- `2` -- Quick DEMO: Momentum (30d)
- `3` -- Quick DEMO: Mean Reversion (30d)
- `4` -- Quick DEMO: Whale Follow (30d)
- `5` -- Quick DEMO: Contrarian (30d)
- `b` -- Back to menu

Without `--demo`, the CLI refuses to run.

## CLI Commands

| Option | Command |
|--------|---------|
| Interactive DEMO | `polyterm backtest --demo -i` |
| Momentum DEMO | `polyterm backtest --demo -s momentum -p 30d` |
| Mean Reversion DEMO | `polyterm backtest --demo -s mean-reversion -p 30d` |
| Whale Follow DEMO | `polyterm backtest --demo -s whale-follow -p 30d` |
| Contrarian DEMO | `polyterm backtest --demo -s contrarian -p 30d` |
| Refused without --demo | `polyterm backtest --format json` |

## Data Sources

- Seeded random number generator (`polyterm/core/demo_strategy_sim.py`)
- Gamma market snapshots used only as labels
- Not local SQLite historical replay, not CLOB price history

## Related Screens

- [benchmark_screen](../screens/benchmark_screen.md) -- compare performance to market averages
- [attribution_screen](../screens/attribution_screen.md) -- analyze performance drivers
- [chart_screen](chart_screen.md) -- real price history charts

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
