# Recent Screen

> View markets you have recently interacted with.

## Overview

The Recent screen shows your recently viewed markets, letting you quickly return to markets you were researching. Markets are automatically tracked as you use PolyTerm, and view counts are recorded for frequently accessed markets.

## Access

- **Menu shortcut**: `rec` or `recent`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A list of recently viewed markets with timestamps and view counts, ordered by most recent access. Provides a quick way to resume research on markets you have been following.

## Navigation / Keyboard Shortcuts

No screen-level shortcuts. The screen runs a single CLI command and displays its output.

## CLI Command

```bash
polyterm recent
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) -- `recently_viewed` table

## Related Screens

- [Bookmarks](../screens/notes.md)
