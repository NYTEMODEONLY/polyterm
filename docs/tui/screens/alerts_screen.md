# Alerts Screen

> View, filter, acknowledge, and test delivery of alerts.

## Overview

The Alerts screen is the full-featured alert management interface. It supports viewing all or unread alerts, filtering by type (whale, insider, arbitrage, smart_money), acknowledging individual alerts by ID, and sending test notifications to Telegram and Discord.

## Access

- **Menu shortcut**: `12`, `alert`
- **Menu path**: Page 1 item 12 (Alerts)

## What It Shows

A submenu with six operations:

1. **View All Alerts** -- recent alerts of all types (configurable limit)
2. **View Unread** -- only unacknowledged alerts
3. **Filter by Type** -- whale, insider, arbitrage, or smart_money
4. **Acknowledge Alert** -- mark a specific alert as read by ID
5. **Test Telegram** -- send a test notification to Telegram
6. **Test Discord** -- send a test notification to Discord

## Navigation / Keyboard Shortcuts

- `1`-`6` to select an operation
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| View all | `polyterm alerts --limit=N` |
| Unread | `polyterm alerts --unread --limit=N` |
| Filter by type | `polyterm alerts --type=TYPE --limit=N` |
| Acknowledge | `polyterm alerts --ack=ID` |
| Test Telegram | `polyterm alerts --test-telegram` |
| Test Discord | `polyterm alerts --test-discord` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)
- Telegram / Discord APIs (for test notifications)

## Related Screens

- [alertcenter_screen](../screens/alertcenter_screen.md) -- simplified alert center view
