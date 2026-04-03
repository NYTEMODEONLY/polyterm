# Parlay

> Calculate combined odds for multi-leg parlays

## Overview

Calculate combined odds for multi-leg parlays. A parlay combines multiple bets - all must win for you to profit.
Higher risk, higher reward!

Examples:
polyterm parlay --markets "0.65,0.70,0.80" --amount 100
polyterm parlay -i   # Interactive mode.

## Usage

### CLI

```bash
polyterm parlay [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `16`, `parlay`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--markets`, `-m` | string | `none` | Comma-separated probabilities (e.g., '0.65,0.70,0.80') |
| `--amount`, `-a` | float | `none` | Bet amount in USD |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm parlay -i

# JSON output
polyterm parlay --format json

# Interactive mode
polyterm parlay --interactive
```


## Related Commands

- [Portfolio](portfolio.md)
- [Position](position.md)
- [Pnl](pnl.md)
- [Simulate](simulate.md)
- [Exit](exit.md)

---

*Source: `polyterm/cli/commands/parlay.py`*
