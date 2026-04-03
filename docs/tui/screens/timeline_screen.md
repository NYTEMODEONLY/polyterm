# Event Timeline

> Visual timeline of upcoming market resolutions.

## Overview

The Event Timeline screen displays a chronological view of markets approaching their resolution dates. It helps traders plan exits and identify opportunities around upcoming events. Supports filtering by time window or bookmarked markets.

## Access

- **Menu shortcut**: `tl` or `timeline`
- **Menu path**: Page 2 → Timeline

## What It Shows

A time-ordered list of markets grouped by resolution date, with countdown indicators showing how soon each market resolves.

## Navigation / Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Next 7 days |
| `2` | Next 30 days (default) |
| `3` | Next 90 days |
| `4` | Bookmarked markets only |
| `b` | Back to main menu |

## CLI Command

```bash
# Next 30 days (default)
polyterm timeline --days 30

# Next 7 days
polyterm timeline --days 7

# Bookmarked markets only
polyterm timeline --bookmarked
```

## Data Sources

- Gamma REST API for market resolution dates
- Local SQLite database for bookmarked market filtering

## Related Screens

- [Calendar](../screens/alertcenter_screen.md)
- [Bookmarks](../screens/notes.md)
