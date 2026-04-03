# Odds

> Convert between different odds formats

## Overview

Convert between different odds formats. Supports: probability, decimal, American, fractional odds.
Helpful for understanding prices and comparing with other platforms.

Examples:
polyterm odds 0.65                    # Convert 65% probability
polyterm odds 2.5 --from decimal      # Convert decimal odds
polyterm odds +150 --from american    # Convert American odds
polyterm odds 3/2 --from fractional   # Convert fractional odds
polyterm odds --market "bitcoin"      # Get odds from market
polyterm odds -i                      # Interactive mode.

## Usage

### CLI

```bash
polyterm odds [value] [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `od`, `odds`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `value` | str | No | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--from`, `-f` | ['prob', 'decimal', 'american', 'fractional'] | `prob` | Input format |
| `--market`, `-m` | string | `none` | Get odds from a market |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm odds <value>

# With from option
polyterm odds <value> --from prob

# JSON output
polyterm odds <value> --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Orderbook](orderbook.md)
- [Depth](depth.md)
- [Trade](trade.md)
- [Quicktrade](quicktrade.md)
- [Size](size.md)

---

*Source: `polyterm/cli/commands/odds.py`*
