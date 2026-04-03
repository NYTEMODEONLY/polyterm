# Scenario

> Model what-if scenarios for your positions

## Overview

Model what-if scenarios for your positions. See how your portfolio would be affected by different outcomes.
Calculate P&L for YES wins, NO wins, or specific probabilities.

Examples:
polyterm scenario --market "bitcoin"   # Analyze one market
polyterm scenario --portfolio          # Analyze all positions.

## Usage

### CLI

```bash
polyterm scenario [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sc`, `scenario`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Specific market to analyze |
| `--portfolio`, `-p` | flag | `false` | Analyze full portfolio |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm scenario

# JSON output
polyterm scenario --format json

# Analyze full portfolio
polyterm scenario --portfolio
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

*Source: `polyterm/cli/commands/scenario.py`*
