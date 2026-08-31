# Backtest

> DEMO strategy simulation. Not historical backtesting.

## Overview

`polyterm backtest` does not replay historical Polymarket trades, order books, or prices. Without `--demo` the command refuses to run. With `--demo` it prints a disclosure first, then generates seeded random trades using current Gamma market snapshots only as labels.

This is a quarantined demo. Do not use the reported Sharpe, win rate, or P&L to choose a strategy. For real historical prices use `polyterm chart` or `polyterm replay`.

This workflow is view-only. It does not place trades or access private keys.

## Usage

### CLI

```bash
polyterm backtest --demo [options]
```

Without `--demo`:

```bash
polyterm backtest --format json
```

returns `success: false`, `mode: "unavailable"`, and `uses_historical_data: false`.

### TUI

Shortcuts: `bt`, `backtest`

The TUI labels the screen as a DEMO simulator and always passes `--demo` to the CLI after showing the disclosure.

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--strategy`, `-s` | ['momentum', 'mean-reversion', 'whale-follow', 'contrarian', 'volume-spike'] | `momentum` | Demo strategy name (changes RNG edge only) |
| `--market`, `-m` | string | `none` | Search term used only as simulation labels |
| `--period`, `-p` | ['7d', '30d', '90d'] | `30d` | Demo window length |
| `--capital`, `-c` | float | `1000` | Starting capital ($) |
| `--position-size` | float | `0.1` | Position size as fraction of capital |
| `--interactive`, `-i` | flag | `false` | Interactive prompts (still requires `--demo`) |
| `--demo` | flag | `false` | Required. Acknowledge this is a random demo |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Refuses: not a historical backtest
polyterm backtest --format json

# Labeled demo simulation
polyterm backtest --demo -s momentum -p 30d --format json
polyterm backtest --demo -i
```

Demo JSON includes `mode: "demo_random_simulation"`, `uses_historical_data: false`, and `disclosure`.

## How It Works

The simulator is `polyterm/core/demo_strategy_sim.py`. It seeds an RNG from the strategy name, samples current Gamma markets for titles/prices, then invents entries, exits, and outcomes. Strategy names do not replay whale wallets or historical fills.

## Data Sources

- Gamma Markets REST API for labels only
- Seeded random number generator
- Not CLOB price history, not Data API trades, not local snapshots as a replay tape

## Related Commands

- [Chart](chart.md) — real CLOB/local price history
- [Replay](replay.md) — replay stored market history
- [History](history.md)
- Core helper: [demo_strategy_sim](../core/demo_strategy_sim.md)

---

*Source: `polyterm/cli/commands/backtest.py`*

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm the linked source file still exists.
- Keep the DEMO / `--demo` requirement in CLI, TUI, and JSON examples.
- Do not describe this command as historical backtesting unless it uses persisted history.
- Run `./test_all_commands.sh` and `.venv/bin/python scripts/validate_docs.py`.
