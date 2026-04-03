# Correlate

> Find correlated and related markets

## Overview

Find correlated and related markets. Discovers markets that may move together based on:
- Topic similarity (title/question matching)
- Category overlap
- Time-based variants (same event, different dates)
- Inverse relationships (opposite outcomes)

Examples:
polyterm correlate -m "bitcoin"           # Find BTC-related markets
polyterm correlate -m "election" -l 20   # More results
polyterm correlate --interactive         # Interactive selection.

## Usage

### CLI

```bash
polyterm correlate [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `corr`, `correlate`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market to find correlations for |
| `--limit`, `-l` | int | `10` | Number of correlated markets to show |
| `--min-score` | float | `0.3` | Minimum correlation score (0-1) |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm correlate -i

# With limit option
polyterm correlate --limit 10

# JSON output
polyterm correlate --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Stats](stats.md)
- [Predict](predict.md)
- [Signals](signals.md)
- [Sentiment](sentiment.md)
- [Benchmark](benchmark.md)

---

*Source: `polyterm/cli/commands/correlate.py`*
