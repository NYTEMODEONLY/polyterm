# Dashboard

> Quick overview of market activity

## Overview

Quick overview of market activity. Shows:
- Top movers (biggest price changes)
- Highest volume markets
- Your bookmarks status
- Alert summary

Perfect for a quick morning check or end-of-day review.

## Usage

### CLI

```bash
polyterm dashboard [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `d`, `dash`, `dashboard`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm dashboard

# JSON output
polyterm dashboard --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Calendar](calendar.md)
- [News](news.md)
- [Leaderboard](leaderboard.md)
- [Health](health.md)
- [Glossary](glossary.md)

---

*Source: `polyterm/cli/commands/dashboard.py`*
