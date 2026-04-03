# Depth

> Analyze order book depth and estimate slippage

## Overview

Analyze order book depth and estimate slippage. Shows liquidity at each price level and estimates execution
price for different trade sizes.

Examples:
polyterm depth -m "bitcoin"              # Analyze depth
polyterm depth -m "election" -s 5000     # For $5000 trade
polyterm depth --interactive             # Interactive mode.

## Usage

### CLI

```bash
polyterm depth [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `dp`, `depth`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market to analyze |
| `--size`, `-s` | float | `1000` | Trade size to analyze ($) |
| `--levels`, `-l` | int | `10` | Number of price levels to show |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm depth -i

# With size option
polyterm depth --size 1000

# JSON output
polyterm depth --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Orderbook](orderbook.md)
- [Trade](trade.md)
- [Quicktrade](quicktrade.md)
- [Size](size.md)
- [Fees](fees.md)

---

*Source: `polyterm/cli/commands/depth.py`*
