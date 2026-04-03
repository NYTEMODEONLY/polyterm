# Bookmarks

> Manage bookmarked markets

## Overview

Manage bookmarked markets. Save markets you want to track or revisit later.

Examples:
polyterm bookmarks --list              # List all bookmarks
polyterm bookmarks --add "bitcoin"     # Bookmark a market
polyterm bookmarks --remove <market_id>  # Remove bookmark.

## Usage

### CLI

```bash
polyterm bookmarks [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `17`, `bm`, `bookmarks`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--list` | flag | `false` | List all bookmarked markets |
| `--add`, `-a` | string | `none` | Add a market to bookmarks (ID or search term) |
| `--remove`, `-r` | string | `none` | Remove a market from bookmarks |
| `--notes`, `-n` | string | `none` | Add notes to a bookmark |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm bookmarks

# JSON output
polyterm bookmarks --format json

# List all bookmarked markets
polyterm bookmarks --list
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Pin](pin.md)
- [Notes](notes.md)
- [Journal](journal.md)
- [Presets](presets.md)
- [Snapshot](snapshot.md)

---

*Source: `polyterm/cli/commands/bookmarks.py`*
