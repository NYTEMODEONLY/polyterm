# Quick

> Quick actions for common trading tasks

## Overview

Quick actions for common trading tasks. One-liner commands for fast market checks and calculations.
Perfect for power users who want speed.

Actions:
price  - Quick price check
buy    - Quick buy calculation
sell   - Quick sell calculation
info   - Quick market info
watch  - Add to watchlist

Examples:
polyterm quick price bitcoin       # Check price
polyterm quick buy "trump wins"    # Calculate buy
polyterm quick info election       # Market info
polyterm quick                     # Interactive menu.

## Usage

### CLI

```bash
polyterm quick [action] [market] [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `qk`, `quick`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `action` | ['price', 'buy', 'sell', 'info', 'watch'] | No | |
| `market` | string | No | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm quick <action> <market>

# JSON output
polyterm quick <action> <market> --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Dashboard](dashboard.md)
- [Calendar](calendar.md)
- [News](news.md)
- [Leaderboard](leaderboard.md)
- [Health](health.md)

---

*Source: `polyterm/cli/commands/quick.py`*
