# Calibrate

> Track your probability calibration

## Overview

Track your probability calibration. Improve your forecasting by tracking how well-calibrated
your probability estimates are. Good traders know their biases.

A well-calibrated predictor has outcomes match probabilities:
- 70% confident predictions should come true ~70% of the time
- 90% confident predictions should come true ~90% of the time

Examples:
polyterm calibrate --add              # Log a new prediction
polyterm calibrate --resolve          # Mark outcome
polyterm calibrate --stats            # View calibration
polyterm calibrate --list             # See all predictions.

## Usage

### CLI

```bash
polyterm calibrate [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `cb`, `calibrate`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--add`, `-a` | flag | `false` | Add a new prediction |
| `--resolve`, `-r` | flag | `false` | Resolve a prediction |
| `--list`, `-l` | flag | `false` | List predictions |
| `--stats`, `-s` | flag | `false` | Show calibration stats |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm calibrate

# JSON output
polyterm calibrate --format json

# Add a new prediction
polyterm calibrate --add
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

*Source: `polyterm/cli/commands/calibrate.py`*
