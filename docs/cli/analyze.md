# Analyze

> Analyze your portfolio for exposure and risk

## Overview

Analyze your portfolio for exposure and risk. Provides insights on:
- Category/sector exposure
- Position concentration
- Win/loss distribution
- Correlation analysis
- Risk metrics

Examples:
polyterm analyze              # Full portfolio analysis
polyterm analyze --format json.

## Usage

### CLI

```bash
polyterm analyze [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `5`, `a`, `an`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm analyze

# JSON output
polyterm analyze --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Config](config.md)
- [Export](export.md)
- [Update](update.md)
- [Lookup](lookup.md)
- [Timing](timing.md)

---

*Source: `polyterm/cli/commands/analytics.py`*
