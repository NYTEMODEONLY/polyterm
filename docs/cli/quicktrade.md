# Quicktrade

> Prepare a trade and get direct Polymarket link

## Overview

Prepare a trade and get direct Polymarket link. Analyzes your trade parameters and provides a direct link to execute
on Polymarket. This tool does NOT execute trades - it prepares the
analysis and opens the market page for you.

Examples:
polyterm quicktrade -m "bitcoin" -a 200 -s yes     # Prepare $200 YES on BTC
polyterm quicktrade -m "trump" -a 50 -s no -o      # Prepare + open browser
polyterm quicktrade -i                              # Interactive mode.

## Usage

### CLI

```bash
polyterm quicktrade [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `qt`, `quicktrade`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market to trade |
| `--amount`, `-a` | float | `100` | Trade amount ($) |
| `--side`, `-s` | ['yes', 'no'] | `none` | Side to buy |
| `--open-browser`, `-o` | flag | `false` | Open Polymarket in browser |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm quicktrade -i

# With amount option
polyterm quicktrade --amount 100

# JSON output
polyterm quicktrade --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Orderbook](orderbook.md)
- [Depth](depth.md)
- [Trade](trade.md)
- [Size](size.md)
- [Fees](fees.md)

---

*Source: `polyterm/cli/commands/quicktrade.py`*
