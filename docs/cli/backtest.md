# Backtest

> Backtest trading strategies on historical data

## Overview

Backtest trading strategies on historical data. Test different strategies to see how they would have performed.
Helps validate trading approaches before risking real capital.

Strategies:
momentum      - Buy rising markets, sell falling
mean-reversion - Buy oversold, sell overbought
whale-follow  - Follow large wallet activity
contrarian    - Fade extreme moves
volume-spike  - Trade on volume spikes

Examples:
polyterm backtest -s momentum -p 30d
polyterm backtest -s whale-follow -m "bitcoin" -c 5000
polyterm backtest -i.

## Usage

### CLI

```bash
polyterm backtest [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `bt`, `backtest`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--strategy`, `-s` | ['momentum', 'mean-reversion', 'whale-follow', 'contrarian', 'volume-spike'] | `momentum` | Strategy to test |
| `--market`, `-m` | string | `none` | Specific market to test on |
| `--period`, `-p` | ['7d', '30d', '90d'] | `30d` | Backtest period |
| `--capital`, `-c` | float | `1000` | Starting capital ($) |
| `--position-size` | float | `0.1` | Position size as fraction of capital |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm backtest -i

# With strategy option
polyterm backtest --strategy momentum

# JSON output
polyterm backtest --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Chart](chart.md)
- [Timeline](timeline.md)
- [History](history.md)
- [Recent](recent.md)
- [Replay](replay.md)

---

*Source: `polyterm/cli/commands/backtest.py`*
