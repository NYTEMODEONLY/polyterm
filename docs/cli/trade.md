# Trade

> Quick trade calculator - analyze before you trade

## Overview

Quick trade calculator - analyze before you trade. Shows everything you need to know before placing a trade:
- Current price and spread
- Estimated shares and avg fill price
- Fees and total cost
- Breakeven and profit scenarios
- Risk/reward analysis

Examples:
polyterm trade -m "bitcoin" -a 500         # Analyze $500 YES trade
polyterm trade -m "election" -s no -a 200  # $200 NO trade
polyterm trade --interactive               # Interactive mode.

## Usage

### CLI

```bash
polyterm trade [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `tr`, `trade`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market to trade |
| `--amount`, `-a` | float | `100` | Trade amount ($) |
| `--side`, `-s` | ['yes', 'no'] | `yes` | Side to buy |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm trade -i

# With amount option
polyterm trade --amount 100

# JSON output
polyterm trade --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Orderbook](orderbook.md)
- [Depth](depth.md)
- [Quicktrade](quicktrade.md)
- [Size](size.md)
- [Fees](fees.md)

---

*Source: `polyterm/cli/commands/trade.py`*
