# Health

> Check your portfolio health

## Overview

Check your portfolio health. Get a comprehensive health score and recommendations.
Analyzes diversification, risk exposure, and trading patterns.

Examples:
polyterm health              # Quick health check
polyterm health --detailed   # Full analysis.

## Usage

### CLI

```bash
polyterm health [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `hp`, `health`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--detailed`, `-d` | flag | `false` | Show detailed breakdown |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm health

# JSON output
polyterm health --format json

# Show detailed breakdown
polyterm health --detailed
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Dashboard](dashboard.md)
- [Calendar](calendar.md)
- [News](news.md)
- [Leaderboard](leaderboard.md)
- [Glossary](glossary.md)

---

*Source: `polyterm/cli/commands/health.py`*
