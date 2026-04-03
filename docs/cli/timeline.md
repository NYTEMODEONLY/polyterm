# Timeline

> Visual timeline of upcoming market resolutions

## Overview

Visual timeline of upcoming market resolutions. Shows when markets are scheduled to resolve, grouped by time period.

Examples:
polyterm timeline                    # Next 30 days
polyterm timeline --days 7           # Next week
polyterm timeline --category crypto  # Crypto markets only
polyterm timeline --bookmarked       # Your bookmarked markets.

## Usage

### CLI

```bash
polyterm timeline [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `tl`, `timeline`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--days`, `-d` | int | `30` | Days to look ahead |
| `--category`, `-c` | string | `none` | Filter by category |
| `--bookmarked`, `-b` | flag | `false` | Show only bookmarked markets |
| `--limit`, `-l` | int | `50` | Maximum markets to show |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm timeline

# With days option
polyterm timeline --days 30

# JSON output
polyterm timeline --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Chart](chart.md)
- [History](history.md)
- [Recent](recent.md)
- [Replay](replay.md)
- [Streak](streak.md)

---

*Source: `polyterm/cli/commands/timeline.py`*
