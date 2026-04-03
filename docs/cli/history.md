# History

> View market price and volume history

## Overview

View market price and volume history. See how a market has evolved over time.
Identify trends, key events, and patterns.

Examples:
polyterm history "bitcoin"              # Last week
polyterm history "trump" --period month # Last month
polyterm history "election" --chart     # With price chart.

## Usage

### CLI

```bash
polyterm history <market_search> [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `hist`, `history`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_search` | string | Yes | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--period`, `-p` | ['day', 'week', 'month', 'all'] | `week` | History period |
| `--chart`, `-c` | flag | `false` | Show price chart |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm history <market_search>

# With period option
polyterm history <market_search> --period week

# JSON output
polyterm history <market_search> --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Chart](chart.md)
- [Timeline](timeline.md)
- [Recent](recent.md)
- [Replay](replay.md)
- [Streak](streak.md)

---

*Source: `polyterm/cli/commands/history.py`*
