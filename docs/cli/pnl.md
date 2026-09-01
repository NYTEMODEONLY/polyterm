# Pnl

> Track your profit & loss over time

## Overview

Track your profit & loss over time. Analyzes locally tracked closed positions (the local journal). For lagged Data API wallet P&L from activity cashflow, use `polyterm mywallet --pnl`.

Examples:
polyterm pnl                   # Last month P&L
polyterm pnl --period week     # Last week
polyterm pnl --period year     # Last year
polyterm pnl --detailed        # Show each trade.

## Usage

### CLI

```bash
polyterm pnl [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `pnl`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--period`, `-p` | ['day', 'week', 'month', 'year', 'all'] | `month` | Time period |
| `--detailed`, `-d` | flag | `false` | Show detailed breakdown |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm pnl

# With period option
polyterm pnl --period month

# JSON output
polyterm pnl --format json
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Portfolio](portfolio.md)
- [Position](position.md)
- [Mywallet](mywallet.md) (`--pnl` is lagged Data API activity cashflow, not this journal)
- [Simulate](simulate.md)
- [Parlay](parlay.md)
- [Exit](exit.md)

---

*Source: `polyterm/cli/commands/pnl.py`*
