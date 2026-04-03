# Digest Screen

> Get a summary of trading and market activity for a selected time period.

## Overview

The Digest screen generates a condensed summary of market and trading activity over a chosen time window. It supports today, yesterday, this week, or this month as time periods, giving a quick recap without needing to dig through individual screens.

## Access

- **Menu shortcut**: `dig` or `digest`
- **Menu path**: Type shortcut from either page

## What It Shows

- Summary of market activity for the selected period
- Key trading metrics and notable events

## Navigation / Keyboard Shortcuts

- **1** - Today (default)
- **2** - Yesterday
- **3** - This week
- **4** - This month
- **b** - Back to menu

## CLI Command

```bash
polyterm digest --period today
polyterm digest --period yesterday
polyterm digest --period week
polyterm digest --period month
```

## Data Sources

- Gamma REST API (market activity data)
- Local SQLite database (tracked activity and history)

## Related Screens

- [Dashboard](../screens/dashboard_screen.md) - real-time activity overview
- [Calendar](../screens/calendar_screen.md) - upcoming market resolutions
