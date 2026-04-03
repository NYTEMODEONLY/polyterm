# Pin

> Pin markets for quick access

## Overview

Pin markets for quick access. Your most important markets always one command away.
Shows current prices and changes at a glance.

Examples:
polyterm pin "bitcoin"       # Pin a market
polyterm pin                 # Show pinned markets
polyterm pin --unpin 1       # Unpin by ID
polyterm pin --refresh       # Update all prices
polyterm pin --clear         # Remove all pins.

## Usage

### CLI

```bash
polyterm pin [market_search] [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `pin`, `pinned`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_search` | string | No | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--unpin`, `-u` | string | `none` | Unpin a market by ID |
| `--clear`, `-c` | flag | `false` | Clear all pinned markets |
| `--refresh`, `-r` | flag | `false` | Refresh pinned market prices |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm pin <market_search>

# JSON output
polyterm pin <market_search> --format json

# Clear all pinned markets
polyterm pin <market_search> --clear
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Bookmarks](bookmarks.md)
- [Notes](notes.md)
- [Journal](journal.md)
- [Presets](presets.md)
- [Snapshot](snapshot.md)

---

*Source: `polyterm/cli/commands/pin.py`*
