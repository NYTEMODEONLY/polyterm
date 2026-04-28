# Simulate

> Simulate a prediction market position

## Overview

Simulate a prediction market position. Calculate potential profit/loss before placing a trade.
Great for understanding how prediction markets work!

Fee estimates use the CLOB V2 protocol fee curve, and market-specific schedules are used when a market can be resolved.

Examples:
polyterm simulate --price 0.65 --amount 100 --side yes
polyterm simulate -i   # Interactive mode.

## Usage

### CLI

```bash
polyterm simulate [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sim`, `simulate`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market ID or name (optional) |
| `--price`, `-p` | float | `none` | Entry price (0.01-0.99) |
| `--amount`, `-a` | float | `none` | Amount to invest in USD |
| `--side`, `-s` | ['yes', 'no'] | `none` | Position side (yes/no) |
| `--interactive`, `-i` | flag | `false` | Interactive mode with prompts |

## Examples

```bash
# Interactive mode
polyterm simulate -i

# Interactive mode with prompts
polyterm simulate --interactive
```


## Related Commands

- [Portfolio](portfolio.md)
- [Position](position.md)
- [Pnl](pnl.md)
- [Parlay](parlay.md)
- [Exit](exit.md)

---

*Source: `polyterm/cli/commands/simulate.py`*
