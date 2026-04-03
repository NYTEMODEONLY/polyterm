# Ev

> Calculate expected value and optimal position size

## Overview

Calculate expected value and optimal position size. The foundation of profitable trading. Enter your probability
estimate to see if a bet has positive expected value.

EV Formula: (Prob * Payout) - (1-Prob * Stake)
Kelly: (bp - q) / b where b=odds, p=win prob, q=lose prob

Examples:
polyterm ev -m "bitcoin" -p 0.65        # Your 65% estimate
polyterm ev -m "election" -p 0.55 -s 500  # $500 stake
polyterm ev -i                          # Interactive mode.

## Usage

### CLI

```bash
polyterm ev [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `ev`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market to analyze |
| `--probability`, `-p` | float | `none` | Your probability estimate (0-1) |
| `--stake`, `-s` | float | `100` | Stake amount ($) |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm ev -i

# With stake option
polyterm ev --stake 100

# JSON output
polyterm ev --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Stats](stats.md)
- [Predict](predict.md)
- [Signals](signals.md)
- [Sentiment](sentiment.md)
- [Correlate](correlate.md)

---

*Source: `polyterm/cli/commands/ev.py`*
