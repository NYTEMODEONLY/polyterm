# Ladder

> Visual price ladder showing depth at each level

## Overview

Visual price ladder showing depth at each level. Shows bid/ask volume at each price tick, like a trading platform.
Helps visualize where support and resistance might be.

Examples:
polyterm ladder "bitcoin"               # Full ladder
polyterm ladder "trump" --side yes      # YES side only
polyterm ladder "election" --levels 15  # More levels.

## Usage

### CLI

```bash
polyterm ladder <market_search> [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `lad`, `ladder`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_search` | string | Yes | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--side`, `-s` | ['yes', 'no', 'both'] | `both` | Which side to show |
| `--levels`, `-l` | int | `10` | Number of price levels |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm ladder <market_search>

# With side option
polyterm ladder <market_search> --side both

# JSON output
polyterm ladder <market_search> --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Orderbook](orderbook.md)
- [Depth](depth.md)
- [Trade](trade.md)
- [Quicktrade](quicktrade.md)
- [Size](size.md)

---

*Source: `polyterm/cli/commands/ladder.py`*
