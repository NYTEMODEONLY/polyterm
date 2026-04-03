# Predict

> Generate signal-based predictions for markets

## Overview

Generate signal-based predictions for markets. Uses momentum, volume, whale activity, and technical indicators
to generate market predictions. All analysis is algorithmic.

## Usage

### CLI

```bash
polyterm predict [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `10`, `pred`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market` | string | `none` | Specific market ID to predict |
| `--limit` | int | `10` | Number of markets to analyze |
| `--horizon` | int | `24` | Prediction horizon in hours |
| `--min-confidence` | float | `0.5` | Minimum confidence threshold |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Basic usage
polyterm predict

# With limit option
polyterm predict --limit 10

# JSON output
polyterm predict --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Stats](stats.md)
- [Signals](signals.md)
- [Sentiment](sentiment.md)
- [Correlate](correlate.md)
- [Benchmark](benchmark.md)

---

*Source: `polyterm/cli/commands/predict.py`*
