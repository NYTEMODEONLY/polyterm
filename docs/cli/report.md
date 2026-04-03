# Report

> Generate comprehensive trading reports

## Overview

Generate comprehensive trading reports. Create detailed reports for analysis and record-keeping.
Reports can be exported to JSON or Markdown format.

Report Types:
daily     - Daily market summary
weekly    - Weekly performance review
portfolio - Your positions and P&L
market    - Deep dive on a specific market

Examples:
polyterm report -t daily               # Daily summary
polyterm report -t portfolio           # Portfolio report
polyterm report -t market -m "bitcoin" # Market analysis
polyterm report -t weekly -o report.md --format markdown.

## Usage

### CLI

```bash
polyterm report [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `rp`, `report`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type`, `-t` | ['daily', 'weekly', 'portfolio', 'market'] | `daily` | Type of report |
| `--market`, `-m` | string | `none` | Specific market for market report |
| `--output`, `-o` | string | `none` | Output file path (optional) |
| `--format` | ['table', 'json', 'markdown'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm report

# With type option
polyterm report --type daily

# JSON output
polyterm report --format json
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

*Source: `polyterm/cli/commands/report.py`*
