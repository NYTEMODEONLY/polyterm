# Leaderboard

> View top traders and your ranking

## Overview

View top traders and your ranking. See the best performers on Polymarket and compare
your performance to the field.

Types:
profit  - Top by realized profit
volume  - Top by trading volume
winrate - Top by win percentage
active  - Most active traders

Examples:
polyterm leaderboard                  # Top by profit
polyterm leaderboard -t winrate       # Top by win rate
polyterm leaderboard --me             # Your ranking
polyterm leaderboard -p 24h -l 50     # Daily, 50 traders.

## Usage

### CLI

```bash
polyterm leaderboard [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `lb`, `leaderboard`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type`, `-t` | ['profit', 'volume', 'winrate', 'active'] | `profit` | Leaderboard type |
| `--period`, `-p` | ['24h', '7d', '30d', 'all'] | `7d` | Time period |
| `--limit`, `-l` | int | `20` | Number of traders to show |
| `--me` | flag | `false` | Show your ranking |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm leaderboard

# With type option
polyterm leaderboard --type profit

# JSON output
polyterm leaderboard --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Dashboard](dashboard.md)
- [Calendar](calendar.md)
- [News](news.md)
- [Health](health.md)
- [Glossary](glossary.md)

---

*Source: `polyterm/cli/commands/leaderboard.py`*
