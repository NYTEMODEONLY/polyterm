# Notification Settings

> Configure how you receive alerts (desktop, sound, webhook).

## Overview

The Notify screen lets you view and modify notification delivery settings. You can enable or disable desktop and sound notifications, configure a webhook URL for external integrations, and test that notifications are working.

## Access

- **Menu shortcut**: `nf` or `notify`
- **Menu path**: Page 2 → Notify

## What It Shows

A menu of six options for managing notification channels:

1. **View current settings** -- shows which channels are enabled
2. **Interactive configuration** -- guided setup wizard
3. **Test notifications** -- sends a test notification to verify delivery
4. **Enable/disable desktop** -- toggle desktop notifications
5. **Enable/disable sound** -- toggle sound notifications
6. **Configure webhook** -- set a webhook URL for external delivery

## Navigation / Keyboard Shortcuts

Standard numbered menu (`1`-`6`, `b` to go back). Options 4 and 5 prompt a follow-up enable/disable choice.

## CLI Commands

| Option | CLI command |
|--------|-------------|
| View settings | `polyterm notify --status` |
| Interactive config | `polyterm notify --configure` |
| Test | `polyterm notify --test` |
| Enable channel | `polyterm notify --enable <desktop\|sound>` |
| Disable channel | `polyterm notify --disable <desktop\|sound>` |
| Set webhook | `polyterm notify --webhook <url>` |

## Data Sources

- Config file (`~/.polyterm/config.toml`)

## Related Screens

- [Price Alerts](../screens/pricealert.md)
- [Alert Center](../screens/alertcenter_screen.md)
