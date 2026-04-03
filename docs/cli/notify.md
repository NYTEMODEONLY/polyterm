# Notify

> Configure notification settings

## Overview

Configure notification settings. Set up how you want to be notified about alerts,
price movements, and other events.

Notification Types:
desktop - Desktop notifications (macOS/Windows/Linux)
sound   - Audible alerts
webhook - HTTP webhook (Discord, Slack, etc.)

Examples:
polyterm notify --status              # View settings
polyterm notify --enable desktop      # Enable desktop
polyterm notify --webhook "https://..." # Set webhook
polyterm notify --test                # Test notifications
polyterm notify -c                    # Interactive config.

## Usage

### CLI

```bash
polyterm notify [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `nf`, `notify`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--status`, `-s` | flag | `false` | Show notification status |
| `--enable` | ['desktop', 'sound', 'webhook'] | `none` | Enable notification type |
| `--disable` | ['desktop', 'sound', 'webhook'] | `none` | Disable notification type |
| `--webhook` | string | `none` | Set webhook URL |
| `--test`, `-t` | flag | `false` | Send test notification |
| `--configure`, `-c` | flag | `false` | Interactive configuration |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm notify

# JSON output
polyterm notify --format json

# Show notification status
polyterm notify --status
```

## Data Sources

- User configuration (`~/.polyterm/config.toml`)


## Related Commands

- [Alerts](alerts.md)
- [Pricealert](pricealert.md)
- [Center](center.md)
- [Watchdog](watchdog.md)

---

*Source: `polyterm/cli/commands/notify.py`*
