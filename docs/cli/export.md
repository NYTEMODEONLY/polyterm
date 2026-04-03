# Export

> Export market data to JSON or CSV

## Overview

Export market data to JSON or CSV.

## Usage

### CLI

```bash
polyterm export [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `7`, `e`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market` | string | `*required*` | Market ID or search term |
| `--format` | ['json', 'csv'] | `json` | Output format |
| `--hours` | int | `24` | Hours of data to export |
| `--output`, `-o` | string | `none` | Output file (default: stdout) |

## Examples

```bash
# Basic usage
polyterm export

# With hours option
polyterm export --hours 48

# JSON output
polyterm export --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Config](config.md)
- [Update](update.md)
- [Lookup](lookup.md)
- [Timing](timing.md)
- [Similar](similar.md)

---

*Source: `polyterm/cli/commands/export_cmd.py`*
