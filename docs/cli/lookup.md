# Lookup

> Quick market lookup - fast info at a glance

## Overview

Quick market lookup - fast info at a glance. Get quick information about a market without navigating menus.
Just type what you're looking for.

Examples:
polyterm lookup bitcoin           # Quick bitcoin market info
polyterm lookup "trump win"       # Search phrase
polyterm lookup 0x123...          # By market ID.

## Usage

### CLI

```bash
polyterm lookup <query> [options]
```

### TUI

Not directly accessible from TUI menu. Use the CLI directly.

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `query` | string | Yes | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm lookup <query>

# JSON output
polyterm lookup <query> --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Config](config.md)
- [Export](export.md)
- [Update](update.md)
- [Timing](timing.md)
- [Similar](similar.md)

---

*Source: `polyterm/cli/commands/lookup.py`*
