# Streak

> Track your winning and losing streaks

## Overview

Track your winning and losing streaks. Understand your trading patterns and psychology.
See current streak, best/worst streaks, and patterns.

Examples:
polyterm streak              # Current streak status
polyterm streak --detailed   # Full streak history.

## Usage

### CLI

```bash
polyterm streak [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `stk`, `streak`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--detailed`, `-d` | flag | `false` | Show detailed streak history |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm streak

# JSON output
polyterm streak --format json

# Show detailed streak history
polyterm streak --detailed
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Chart](chart.md)
- [Timeline](timeline.md)
- [History](history.md)
- [Recent](recent.md)
- [Replay](replay.md)

---

*Source: `polyterm/cli/commands/streak.py`*
