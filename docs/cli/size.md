# Size

> Calculate optimal position size

## Overview

Calculate optimal position size. Uses Kelly Criterion and other strategies to recommend bet sizes
based on your edge and bankroll.

Kelly and EV estimates account for the CLOB V2 protocol fee curve instead of a fixed taker-fee assumption.

Examples:
polyterm size --bankroll 1000 --probability 0.65 --odds 0.50
polyterm size -i   # Interactive mode.

## Usage

### CLI

```bash
polyterm size [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sz`, `size`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--bankroll`, `-b` | float | `none` | Your total bankroll/budget |
| `--probability`, `-p` | float | `none` | Your estimated probability (0.01-0.99) |
| `--odds`, `-o` | float | `none` | Market price/odds (0.01-0.99) |
| `--kelly`, `-k` | float | `0.25` | Kelly fraction (default: 0.25 = quarter Kelly) |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm size -i

# With kelly option
polyterm size --kelly 0.25

# JSON output
polyterm size --format json
```


## Related Commands

- [Orderbook](orderbook.md)
- [Depth](depth.md)
- [Trade](trade.md)
- [Quicktrade](quicktrade.md)
- [Fees](fees.md)

---

*Source: `polyterm/cli/commands/size.py`*
