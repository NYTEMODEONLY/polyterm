# Streak Tracker

> Track winning and losing streaks across your prediction market trades.

## Overview

The Streak Tracker screen shows your current and historical trading streaks. It helps identify momentum in your trading performance and patterns of consecutive wins or losses.

## Access

- **Menu shortcut**: `stk` or `streak`
- **Menu path**: Page 2 → Streak Tracker

## What It Shows

Two viewing modes:

1. **Current streak status** -- Your active win/loss streak summary.
2. **Detailed streak history** -- Full breakdown of past streaks over time.

## Navigation / Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Current streak status |
| `2` | Detailed streak history |
| `b` | Back to main menu |

## CLI Command

```bash
# Current streak status
polyterm streak

# Detailed streak history
polyterm streak --detailed
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for trade history

## Related Screens

- [Journal](../screens/journal_screen.md)
- [Timing Analysis](../screens/timing_screen.md)
