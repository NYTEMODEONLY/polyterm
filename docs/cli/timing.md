# Timing

> Analyze optimal timing for trading a market

## Overview

Analyze optimal timing for trading a market. Combines spread, volume, and momentum analysis to suggest
the best times and conditions for entry/exit.

Examples:
polyterm timing "bitcoin"    # Full timing analysis
polyterm timing "trump"      # Check trading conditions.

## Usage

### CLI

```bash
polyterm timing <market_search> [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `tm`, `timing`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_search` | string | Yes | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm timing <market_search>

# JSON output
polyterm timing <market_search> --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Config](config.md)
- [Export](export.md)
- [Update](update.md)
- [Lookup](lookup.md)
- [Similar](similar.md)

---

*Source: `polyterm/cli/commands/timing.py`*
