# Digest

> Get a summary of trading and market activity

## Overview

Get a summary of trading and market activity. Quick catch-up on what happened while you were away.
Includes your P&L, market movers, and upcoming events.

Examples:
polyterm digest                  # Today's summary
polyterm digest --period week    # Weekly summary
polyterm digest --period yesterday  # Yesterday's recap.

## Usage

### CLI

```bash
polyterm digest [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `dig`, `digest`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--period`, `-p` | ['today', 'yesterday', 'week', 'month'] | `today` | Summary period |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm digest

# With period option
polyterm digest --period today

# JSON output
polyterm digest --format json
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

*Source: `polyterm/cli/commands/digest.py`*
