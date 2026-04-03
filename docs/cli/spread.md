# Spread

> Analyze bid/ask spread and execution costs

## Overview

Analyze bid/ask spread and execution costs. Understand the true cost of trading before you execute.
Shows spread, slippage estimates, and execution quality.

Examples:
polyterm spread "bitcoin"              # Basic spread analysis
polyterm spread "trump" --amount 500   # Cost for $500 trade.

## Usage

### CLI

```bash
polyterm spread <market_search> [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sp`, `spread`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_search` | string | Yes | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--amount`, `-a` | float | `100` | Trade amount in USD |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm spread <market_search>

# With amount option
polyterm spread <market_search> --amount 100

# JSON output
polyterm spread <market_search> --format json
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

*Source: `polyterm/cli/commands/spread.py`*
