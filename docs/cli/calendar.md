# Calendar

> View upcoming market resolutions

## Overview

View upcoming market resolutions. Shows markets that are ending soon, helping you plan trades
and avoid getting stuck in positions near resolution.

Examples:
polyterm calendar                     # Next 7 days
polyterm calendar --days 30           # Next 30 days
polyterm calendar --category crypto   # Crypto markets only
polyterm calendar --bookmarked        # Only bookmarked markets.

## Usage

### CLI

```bash
polyterm calendar [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `cal`, `calendar`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--days`, `-d` | int | `7` | Days to look ahead (default: 7) |
| `--limit`, `-l` | int | `20` | Maximum markets to show (default: 20) |
| `--category`, `-c` | string | `none` | Filter by category (e.g., politics, crypto) |
| `--bookmarked`, `-b` | flag | `false` | Only show bookmarked markets |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm calendar

# With days option
polyterm calendar --days 7

# JSON output
polyterm calendar --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Dashboard](dashboard.md)
- [News](news.md)
- [Leaderboard](leaderboard.md)
- [Health](health.md)
- [Glossary](glossary.md)

---

*Source: `polyterm/cli/commands/calendar.py`*
