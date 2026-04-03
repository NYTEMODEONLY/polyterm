# Benchmark

> Compare your performance to market benchmarks

## Overview

Compare your performance to market benchmarks. See how you stack up against:
- Market average returns
- Win rate benchmarks
- Category-specific performance

Examples:
polyterm benchmark                    # Monthly comparison
polyterm benchmark --period quarter   # Quarterly view
polyterm benchmark --detailed         # Full breakdown.

## Usage

### CLI

```bash
polyterm benchmark [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `bench`, `benchmark`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--period`, `-p` | ['week', 'month', 'quarter', 'year', 'all'] | `month` | Time period |
| `--detailed`, `-d` | flag | `false` | Show detailed breakdown |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm benchmark

# With period option
polyterm benchmark --period month

# JSON output
polyterm benchmark --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Stats](stats.md)
- [Predict](predict.md)
- [Signals](signals.md)
- [Sentiment](sentiment.md)
- [Correlate](correlate.md)

---

*Source: `polyterm/cli/commands/benchmark.py`*
