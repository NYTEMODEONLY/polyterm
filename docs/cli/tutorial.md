# Tutorial

> Interactive tutorial for new users

## Overview

Interactive tutorial for new users. Learn how prediction markets work and how to use PolyTerm effectively.

## Usage

### CLI

```bash
polyterm tutorial [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `t`, `tut`, `tutorial`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--step` | int | `0` | Start from specific step (0-indexed) |
| `--quick` | flag | `false` | Quick mode - no pauses |

## Examples

```bash
# Basic usage
polyterm tutorial

# With step option
polyterm tutorial --step 0

# Quick mode - no pauses
polyterm tutorial --quick
```


## Related Commands

- [Dashboard](dashboard.md)
- [Calendar](calendar.md)
- [News](news.md)
- [Leaderboard](leaderboard.md)
- [Health](health.md)

---

*Source: `polyterm/cli/commands/tutorial.py`*
