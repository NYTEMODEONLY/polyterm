# Calendar Screen

> View upcoming market resolutions to plan trades and exits.

## Overview

The Calendar screen displays markets that are approaching their resolution date. This helps traders plan ahead by showing which markets are ending soon, enabling timely exits or last-minute entries before resolution.

## Access

- **Menu shortcut**: `cal` or `calendar`
- **Menu path**: Type shortcut from either page

## What It Shows

- Markets grouped by resolution date
- Countdown to each market's resolution
- Configurable lookahead window (defaults to 7 days)

## Navigation / Keyboard Shortcuts

- Prompted for number of days to look ahead (default: 7)
- Returns to menu when the command completes

## CLI Command

```bash
polyterm calendar --days <days>
```

## Data Sources

- Gamma REST API (market end dates and metadata)

## Related Screens

- [Dashboard](../screens/dashboard_screen.md) - also shows upcoming activity
- [Chart](../screens/chart_screen.md) - view price history before resolution
