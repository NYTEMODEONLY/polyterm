# Position

> Track positions and P&L manually

## Overview

Track positions and P&L manually. Track your trades without connecting a wallet. Useful for:
- Paper trading and tracking hypothetical positions
- Privacy (no wallet connection needed)
- Tracking positions across multiple platforms

Examples:
polyterm position --list                # List all positions
polyterm position --add "bitcoin"       # Add new position
polyterm position --close 1             # Close position #1
polyterm position --summary             # View P&L summary
polyterm position -i                    # Interactive mode.

## Usage

### CLI

```bash
polyterm position [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `pos`, `position`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--list`, `-l` | flag | `false` | List all positions |
| `--open` | flag | `false` | Show only open positions |
| `--closed` | flag | `false` | Show only closed positions |
| `--add`, `-a` | string | `none` | Add position for market |
| `--close`, `-c` | int | `none` | Close position by ID |
| `--delete`, `-d` | int | `none` | Delete position by ID |
| `--summary`, `-s` | flag | `false` | Show P&L summary |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm position -i

# JSON output
polyterm position --format json

# List all positions
polyterm position --list
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Portfolio](portfolio.md)
- [Pnl](pnl.md)
- [Simulate](simulate.md)
- [Parlay](parlay.md)
- [Exit](exit.md)

---

*Source: `polyterm/cli/commands/position.py`*
