# Chart

> Display price history chart for a market

## Overview

Display price history chart for a market. Shows ASCII chart of price movement over time.

Examples:
polyterm chart --market "bitcoin"
polyterm chart -m "election" --hours 48
polyterm chart -m "bitcoin" --sparkline.

## Usage

### CLI

```bash
polyterm chart [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `ch`, `chart`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market ID or search term |
| `--hours`, `-h` | int | `24` | Hours of history (default: 24) |
| `--width`, `-w` | int | `50` | Chart width (default: 50) |
| `--height` | int | `12` | Chart height (default: 12) |
| `--sparkline`, `-s` | flag | `false` | Show compact sparkline instead of full chart |
| `--format` | ['chart', 'json'] | `chart` |  |

## Examples

```bash
# Basic usage
polyterm chart

# With hours option
polyterm chart --hours 48

# JSON output
polyterm chart --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Timeline](timeline.md)
- [History](history.md)
- [Recent](recent.md)
- [Replay](replay.md)
- [Streak](streak.md)

---

*Source: `polyterm/cli/commands/chart.py`*
