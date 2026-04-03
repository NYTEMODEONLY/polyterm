# Journal

> Trade journal for documenting your trades

## Overview

Trade journal for documenting your trades. Keep track of your trading decisions, lessons learned,
and insights for continuous improvement.

Examples:
polyterm journal --list               # List entries
polyterm journal --add                # Add new entry
polyterm journal --view 1             # View entry #1
polyterm journal --search "bitcoin"   # Search entries
polyterm journal --tag "lesson"       # Filter by tag.

## Usage

### CLI

```bash
polyterm journal [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `jn`, `journal`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--list`, `-l` | flag | `false` | List journal entries |
| `--add`, `-a` | flag | `false` | Add new journal entry |
| `--view`, `-v` | int | `none` | View entry by ID |
| `--delete`, `-d` | int | `none` | Delete entry by ID |
| `--search`, `-s` | string | `none` | Search entries |
| `--tag`, `-t` | string | `none` | Filter by tag |
| `--limit` | int | `20` | Number of entries to show |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm journal

# With limit option
polyterm journal --limit 10

# JSON output
polyterm journal --format json
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Bookmarks](bookmarks.md)
- [Pin](pin.md)
- [Notes](notes.md)
- [Presets](presets.md)
- [Snapshot](snapshot.md)

---

*Source: `polyterm/cli/commands/journal.py`*
