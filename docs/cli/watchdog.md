# Watchdog

> Continuous monitoring with custom alert conditions

## Overview

Continuous monitoring with custom alert conditions. Watch markets and alert when conditions are met.
Runs until stopped (Ctrl+C) or duration expires.

Examples:
polyterm watchdog -m "bitcoin" --above 0.70
polyterm watchdog -m "trump" --below 0.40
polyterm watchdog -m "btc" -m "eth" --change 0.05
polyterm watchdog -m "election" --volume 100000.

## Usage

### CLI

```bash
polyterm watchdog [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `wd`, `watchdog`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Markets to watch (can specify multiple) |
| `--above`, `-a` | float | `none` | Alert when price goes above |
| `--below`, `-b` | float | `none` | Alert when price goes below |
| `--change`, `-c` | float | `none` | Alert on price change (e.g., 0.05 for 5%) |
| `--volume`, `-v` | float | `none` | Alert when 24h volume exceeds |
| `--interval`, `-i` | int | `30` | Check interval in seconds |
| `--duration`, `-d` | int | `0` | Duration in minutes (0 = until stopped) |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm watchdog -i

# With interval option
polyterm watchdog --interval 30

# JSON output
polyterm watchdog --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Alerts](alerts.md)
- [Pricealert](pricealert.md)
- [Center](center.md)
- [Notify](notify.md)

---

*Source: `polyterm/cli/commands/watchdog.py`*
