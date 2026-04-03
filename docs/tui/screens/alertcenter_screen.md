# Alert Center Screen

> Unified view of all alerts and notifications with management options.

## Overview

The Alert Center provides a centralized hub for viewing and managing all PolyTerm alerts. It offers options to view active alerts, check for new ones, see acknowledged alerts, or clear all alerts at once.

## Access

- **Menu shortcut**: `ac`, `center`, `alertcenter`
- **Menu path**: Extended shortcuts menu

## What It Shows

A simple options menu with four actions:

1. **View active alerts** -- shows current unacknowledged alerts
2. **Check for new alerts** -- scans for newly triggered alerts
3. **View all (incl. acknowledged)** -- shows the full alert history
4. **Clear all alerts** -- removes all stored alerts

## Navigation / Keyboard Shortcuts

- `1`-`4` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| View active | `polyterm center` |
| Check new | `polyterm center --check` |
| View all | `polyterm center --all` |
| Clear all | `polyterm center --clear` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)

## Related Screens

- [alerts_screen](../screens/alerts_screen.md) -- the numbered-menu alerts screen with type filtering and notification testing
