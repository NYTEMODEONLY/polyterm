# Recent

> View recently accessed markets

## Overview

View recently accessed markets. Shows markets you've recently viewed, searched for, or interacted with.
Helpful for quickly returning to markets you were researching.

Examples:
polyterm recent                   # Show recent markets
polyterm recent -m                # Show most viewed
polyterm recent --clear           # Clear history
polyterm recent -o 1              # Open first market.

## Usage

### CLI

```bash
polyterm recent [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `rec`, `recent`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--limit`, `-l` | int | `15` | Number of recent markets to show (default: 15) |
| `--most-viewed`, `-m` | flag | `false` | Sort by view count instead of recency |
| `--clear`, `-c` | flag | `false` | Clear recent history |
| `--open`, `-o` | string | `none` | Open a recent market by number |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm recent

# With limit option
polyterm recent --limit 10

# JSON output
polyterm recent --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Chart](chart.md)
- [Timeline](timeline.md)
- [History](history.md)
- [Replay](replay.md)
- [Streak](streak.md)

---

*Source: `polyterm/cli/commands/recent.py`*
