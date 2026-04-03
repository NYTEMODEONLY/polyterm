# Dashboard Screen

> Quick overview of market activity, bookmarks, alerts, and followed wallets.

## Overview

The Dashboard screen provides a consolidated snapshot of your PolyTerm activity. It clears the terminal and displays top volume markets, bookmarked markets, active alerts, and followed wallets in a single view. Designed for daily check-ins.

## Access

- **Menu shortcut**: `d`, `dash`, or `dashboard`
- **Menu path**: Page 1 (listed as "Dashboard")

## What It Shows

- Top markets by volume
- Bookmarked markets and their current status
- Active price alerts
- Followed wallet activity summaries

## Navigation / Keyboard Shortcuts

- No interactive prompts; the dashboard renders immediately
- Press Enter to return to the main menu

## CLI Command

```bash
polyterm dashboard
```

## Data Sources

- Gamma REST API (market data and volumes)
- Local SQLite database (bookmarks, alerts, followed wallets)

## Related Screens

- [Monitor](../screens/monitor_screen.md) - detailed market monitoring
- [Alerts](../screens/alerts_screen.md) - manage price alerts
- [Bookmarks](../screens/bookmarks_screen.md) - manage saved markets
