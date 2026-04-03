# Exit Strategy Planner

> Plan profit targets and stop losses for your positions.

## Overview

The Exit Strategy Planner helps you define when to take profits or cut losses on market positions. You can create new exit plans with target prices or review previously saved plans. This screen provides a structured approach to trade management rather than making ad-hoc exit decisions.

## Access

- **Menu shortcut**: `ex` or `exitplan`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A menu with two options:

1. **Plan exit for a position** -- launches the interactive exit planner where you set profit targets and stop-loss levels
2. **View saved exit plans** -- lists previously created exit strategies

## Navigation / Keyboard Shortcuts

- `1` -- Plan a new exit strategy
- `2` -- View saved exit plans
- `b` -- Back to main menu

## CLI Command

```bash
# Interactive exit planning
polyterm exit --interactive

# List saved exit plans
polyterm exit --list
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for saved exit plans
- Gamma API for current market prices

## Related Screens

- [Fees](../screens/fees.md) -- understand costs affecting exit targets
- [Hot Markets](../screens/hot.md) -- identify markets with momentum for exit timing
