# Sentiment

> Analyze market sentiment from multiple signals

## Overview

Analyze market sentiment from multiple signals. Combines volume, price momentum, whale activity, and order book
data to provide an overall sentiment score.

Examples:
polyterm sentiment -m "bitcoin"       # Sentiment for market
polyterm sentiment --interactive      # Interactive selection.

## Usage

### CLI

```bash
polyterm sentiment [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sent`, `sentiment`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market to analyze |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm sentiment -i

# JSON output
polyterm sentiment --format json

# Interactive mode
polyterm sentiment --interactive
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- Local SQLite database (`~/.polyterm/data.db`)
- WebSocket real-time feed


## Related Commands

- [Stats](stats.md)
- [Predict](predict.md)
- [Signals](signals.md)
- [Correlate](correlate.md)
- [Benchmark](benchmark.md)

---

*Source: `polyterm/cli/commands/sentiment.py`*
