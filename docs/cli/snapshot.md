# Snapshot

> Save and compare market states over time

## Overview

Save and compare market states over time. Take snapshots of market data to track how they evolve.
Compare past snapshots to current state.

Examples:
polyterm snapshot --save "bitcoin"       # Save current state
polyterm snapshot --list                 # List snapshots
polyterm snapshot --compare 1            # Compare snapshot #1 to now
polyterm snapshot --view 1               # View snapshot details.

## Usage

### CLI

```bash
polyterm snapshot [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `snap`, `snapshot`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--save`, `-s` | string | `none` | Save snapshot of a market |
| `--list`, `-l` | flag | `false` | List saved snapshots |
| `--view`, `-v` | int | `none` | View snapshot by ID |
| `--compare`, `-c` | int | `none` | Compare snapshot to current state |
| `--delete`, `-d` | int | `none` | Delete snapshot |
| `--market`, `-m` | string | `none` | Filter by market |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm snapshot

# JSON output
polyterm snapshot --format json

# List saved snapshots
polyterm snapshot --list
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Bookmarks](bookmarks.md)
- [Pin](pin.md)
- [Notes](notes.md)
- [Journal](journal.md)
- [Presets](presets.md)

---

*Source: `polyterm/cli/commands/snapshot.py`*
