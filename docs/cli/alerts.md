# Alerts

> View and manage alerts

## Overview

View and manage alerts.

## Usage

### CLI

```bash
polyterm alerts [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `12`, `alert`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | ['all', 'whale', 'insider', 'arbitrage', 'smart_money'] | `all` | Filter by alert type |
| `--limit` | int | `20` | Maximum alerts to show |
| `--unread` | flag | `false` | Show only unacknowledged alerts |
| `--ack` | int | `none` | Acknowledge alert by ID |
| `--test-telegram` | flag | `false` | Send test Telegram notification |
| `--test-discord` | flag | `false` | Send test Discord notification |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Basic usage
polyterm alerts

# With type option
polyterm alerts --type all

# JSON output
polyterm alerts --format json
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)
- User configuration (`~/.polyterm/config.toml`)


## Related Commands

- [Pricealert](pricealert.md)
- [Center](center.md)
- [Watchdog](watchdog.md)
- [Notify](notify.md)

---

*Source: `polyterm/cli/commands/alerts.py`*
