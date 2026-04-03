# Fees

> Calculate trading fees and slippage

## Overview

Calculate trading fees and slippage. Understand the true cost of your trades including:
- Platform fees (2% on winnings)
- Estimated slippage based on order book
- Gas fees for on-chain transactions

Examples:
polyterm fees --amount 100 --price 0.65
polyterm fees -a 1000 -p 0.50 --market "bitcoin"
polyterm fees -i   # Interactive mode.

## Usage

### CLI

```bash
polyterm fees [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `fee`, `fees`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--amount`, `-a` | float | `none` | Trade amount in USD |
| `--price`, `-p` | float | `none` | Market price (0.01-0.99) |
| `--market`, `-m` | string | `none` | Market ID or search term (for slippage) |
| `--side`, `-s` | ['buy', 'sell'] | `buy` | Trade side |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm fees -i

# With side option
polyterm fees --side buy

# JSON output
polyterm fees --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API


## Related Commands

- [Orderbook](orderbook.md)
- [Depth](depth.md)
- [Trade](trade.md)
- [Quicktrade](quicktrade.md)
- [Size](size.md)

---

*Source: `polyterm/cli/commands/fees.py`*
