# Notes

> Manage personal notes on markets

## Overview

Manage personal notes on markets. Keep track of your research, thesis, and thoughts on markets.

Examples:
polyterm notes --list                    # List all notes
polyterm notes --add "bitcoin"           # Add note for market
polyterm notes --view "bitcoin"          # View existing note
polyterm notes --delete "market_id"      # Delete note.

## Usage

### CLI

```bash
polyterm notes [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `nt`, `notes`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--list`, `-l` | flag | `false` | List all market notes |
| `--add`, `-a` | string | `none` | Add note for market (ID or search) |
| `--view`, `-v` | string | `none` | View note for market |
| `--delete`, `-d` | string | `none` | Delete note for market |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm notes

# JSON output
polyterm notes --format json

# List all market notes
polyterm notes --list
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Bookmarks](bookmarks.md)
- [Pin](pin.md)
- [Journal](journal.md)
- [Presets](presets.md)
- [Snapshot](snapshot.md)

---

*Source: `polyterm/cli/commands/notes.py`*
