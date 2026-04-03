# Presets

> Manage saved search filter presets

## Overview

Manage saved search filter presets. Save commonly used search filters and quickly rerun them.

Examples:
polyterm presets --list                    # List saved presets
polyterm presets --save "high-volume"      # Save current filters
polyterm presets --run "high-volume"       # Run saved preset
polyterm presets --interactive             # Create preset interactively
polyterm presets --delete "old-preset"     # Delete a preset.

## Usage

### CLI

```bash
polyterm presets [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `pr`, `presets`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--list`, `-l` | flag | `false` | List all saved presets |
| `--save`, `-s` | string | `none` | Save current filters as preset |
| `--run`, `-r` | string | `none` | Run a saved preset |
| `--delete`, `-d` | string | `none` | Delete a preset |
| `--view`, `-v` | string | `none` | View preset filters |
| `--interactive`, `-i` | flag | `false` | Interactive preset creation |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm presets -i

# JSON output
polyterm presets --format json

# List all saved presets
polyterm presets --list
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Bookmarks](bookmarks.md)
- [Pin](pin.md)
- [Notes](notes.md)
- [Journal](journal.md)
- [Snapshot](snapshot.md)

---

*Source: `polyterm/cli/commands/presets.py`*
