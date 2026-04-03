# Similar

> Find markets similar to a given market

## Overview

Find markets similar to a given market. Useful for:
- Diversification (find related bets)
- Hedging (find correlated markets)
- Discovery (explore related topics)

Examples:
polyterm similar "bitcoin"              # Find markets like bitcoin
polyterm similar "trump" --type topic   # Topic-based similarity
polyterm similar "election" --limit 20  # More results.

## Usage

### CLI

```bash
polyterm similar <market_search> [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sml`, `similar`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_search` | string | Yes | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--limit`, `-l` | int | `10` | Number of similar markets to show |
| `--type`, `-t` | ['topic', 'category', 'all'] | `all` | Similarity type |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm similar <market_search>

# With limit option
polyterm similar <market_search> --limit 10

# JSON output
polyterm similar <market_search> --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Config](config.md)
- [Export](export.md)
- [Update](update.md)
- [Lookup](lookup.md)
- [Timing](timing.md)

---

*Source: `polyterm/cli/commands/similar.py`*
