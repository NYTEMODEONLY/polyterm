# Center

> Unified alert center for all notifications

## Overview

Unified alert center for all notifications. View and manage all your alerts in one place:
- Price alerts (targets hit)
- Whale activity alerts
- Resolution alerts (markets ending)
- Position alerts (P&L thresholds)

Examples:
polyterm center                  # View active alerts
polyterm center --all            # Include acknowledged
polyterm center --type price     # Only price alerts
polyterm center --check          # Check for new alerts
polyterm center --clear          # Clear all alerts.

## Usage

### CLI

```bash
polyterm center [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `ac`, `center`, `alertcenter`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--all`, `-a` | flag | `false` | Show all alerts including acknowledged |
| `--type`, `-t` | string | `none` | Filter by type (price, whale, resolution) |
| `--clear`, `-c` | flag | `false` | Clear all alerts |
| `--check` | flag | `false` | Check for new alerts |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm center

# JSON output
polyterm center --format json

# Show all alerts including acknowledged
polyterm center --all
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Alerts](alerts.md)
- [Pricealert](pricealert.md)
- [Watchdog](watchdog.md)
- [Notify](notify.md)

---

*Source: `polyterm/cli/commands/alertcenter.py`*
