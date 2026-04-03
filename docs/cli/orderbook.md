# Orderbook

> Analyze order book for a market

## Overview

Analyze order book for a market. MARKET_ID is the market token ID to analyze.

## Usage

### CLI

```bash
polyterm orderbook <market_id> [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `13`, `ob`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_id` | string | Yes | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--depth` | int | `20` | Order book depth |
| `--chart` | flag | `false` | Show ASCII depth chart |
| `--live` | flag | `false` | Live WebSocket feed (updates in real-time) |
| `--refresh` | float | `1.0` | Live refresh interval in seconds |
| `--slippage` | float | `none` | Calculate slippage for order size |
| `--side` | ['buy', 'sell'] | `buy` | Order side for slippage |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Basic usage
polyterm orderbook <market_id>

# With depth option
polyterm orderbook <market_id> --depth 30

# JSON output
polyterm orderbook <market_id> --format json
```

## Data Sources

- CLOB REST API
- Local SQLite database (`~/.polyterm/data.db`)
- WebSocket real-time feed


## Related Commands

- [Depth](depth.md)
- [Trade](trade.md)
- [Quicktrade](quicktrade.md)
- [Size](size.md)
- [Fees](fees.md)

---

*Source: `polyterm/cli/commands/orderbook.py`*
