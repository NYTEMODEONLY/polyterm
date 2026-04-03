# Pricealert

> Set price alerts for markets

## Overview

Set price alerts for markets. Get notified when markets reach your target prices.

Examples:
polyterm pricealert --list              # List active alerts
polyterm pricealert --add "bitcoin"     # Add alert for market
polyterm pricealert --check             # Check if any alerts triggered
polyterm pricealert -i                  # Interactive mode.

## Usage

### CLI

```bash
polyterm pricealert [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `pa`, `pricealert`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--list`, `-l` | flag | `false` | List all active price alerts |
| `--add`, `-a` | string | `none` | Add alert for market (ID or search term) |
| `--remove`, `-r` | int | `none` | Remove alert by ID |
| `--check`, `-c` | flag | `false` | Check alerts against current prices |
| `--all` | flag | `false` | Show all alerts including triggered |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm pricealert -i

# JSON output
polyterm pricealert --format json

# List all active price alerts
polyterm pricealert --list
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Alerts](alerts.md)
- [Center](center.md)
- [Watchdog](watchdog.md)
- [Notify](notify.md)

---

*Source: `polyterm/cli/commands/pricealert.py`*
