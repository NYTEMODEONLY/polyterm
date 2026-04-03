# Stats

> View detailed market statistics

## Overview

View detailed market statistics. Shows volatility, price trends, volume analysis, and technical indicators.

Examples:
polyterm stats --market "bitcoin"
polyterm stats -m "election" --hours 48.

## Usage

### CLI

```bash
polyterm stats [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `st`, `stats`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market ID or search term |
| `--hours`, `-h` | int | `24` | Hours of history for analysis (default: 24) |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm stats

# With hours option
polyterm stats --hours 48

# JSON output
polyterm stats --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Predict](predict.md)
- [Signals](signals.md)
- [Sentiment](sentiment.md)
- [Correlate](correlate.md)
- [Benchmark](benchmark.md)

---

*Source: `polyterm/cli/commands/stats.py`*
