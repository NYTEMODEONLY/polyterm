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
