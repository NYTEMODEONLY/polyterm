# Exit

> Plan exit strategies with profit targets and stop losses

## Overview

Plan exit strategies with profit targets and stop losses. Calculates breakeven, profit targets, and risk/reward ratios.
Saves plans that can be checked against price alerts.

Examples:
polyterm exit -m "bitcoin" -e 0.65 -s 100    # Plan exit
polyterm exit --interactive                   # Interactive mode
polyterm exit --list                          # View saved plans.

## Usage

### CLI

```bash
polyterm exit [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `ex`, `exitplan`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market to plan exit for |
| `--entry`, `-e` | float | `none` | Your entry price (0-1) |
| `--shares`, `-s` | float | `none` | Number of shares |
| `--side` | ['yes', 'no'] | `yes` | Position side |
| `--list`, `-l` | flag | `false` | List saved exit plans |
| `--delete`, `-d` | int | `none` | Delete exit plan by ID |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm exit -i

# With side option
polyterm exit --side yes

# JSON output
polyterm exit --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Portfolio](portfolio.md)
- [Position](position.md)
- [Pnl](pnl.md)
- [Simulate](simulate.md)
- [Parlay](parlay.md)

---

*Source: `polyterm/cli/commands/exit.py`*
