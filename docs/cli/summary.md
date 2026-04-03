# Summary

> Get a quick one-line market summary

## Overview

Get a quick one-line market summary. Super fast way to check a market's status.
Perfect for quick checks and scripting.

Examples:
polyterm summary "bitcoin"              # Quick one-liner
polyterm summary "trump" --format json  # JSON for scripts.

## Usage

### CLI

```bash
polyterm summary <market_search> [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sum`, `summary`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_search` | string | Yes | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | ['table', 'json', 'oneline'] | `oneline` |  |

## Examples

```bash
# Basic usage
polyterm summary <market_search>

# JSON output
polyterm summary <market_search> --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Bookmarks](bookmarks.md)
- [Pin](pin.md)
- [Notes](notes.md)
- [Journal](journal.md)
- [Presets](presets.md)

---

*Source: `polyterm/cli/commands/summary.py`*
