# Signals

> Detect entry and exit signals for markets

## Overview

Detect entry and exit signals for markets. Analyzes multiple factors to generate trading signals:
- Volume spikes (unusual activity)
- Price momentum (breakouts/breakdowns)
- Whale activity (accumulation/distribution)
- Technical indicators (overbought/oversold)

Examples:
polyterm signals --market "bitcoin"     # Analyze specific market
polyterm signals --scan                 # Scan for opportunities
polyterm signals --type entry           # Entry signals only
polyterm signals --min-strength 70      # Strong signals only.

## Usage

### CLI

```bash
polyterm signals [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sig`, `signals`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Analyze specific market |
| `--scan`, `-s` | flag | `false` | Scan all markets for signals |
| `--type`, `-t` | ['all', 'entry', 'exit'] | `all` | Signal type |
| `--min-strength` | int | `60` | Minimum signal strength (0-100) |
| `--limit`, `-l` | int | `20` | Number of markets to scan |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm signals

# With type option
polyterm signals --type all

# JSON output
polyterm signals --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Stats](stats.md)
- [Predict](predict.md)
- [Sentiment](sentiment.md)
- [Correlate](correlate.md)
- [Benchmark](benchmark.md)

---

*Source: `polyterm/cli/commands/signals.py`*
