# Arbitrage

> Scan for arbitrage opportunities across markets

## Overview

Scan for arbitrage opportunities across markets.

## Usage

### CLI

```bash
polyterm arbitrage [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `9`, `arb`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--min-spread` | float | `0.025` | Minimum spread for arbitrage (default: 2.5%) |
| `--limit` | int | `10` | Maximum opportunities to show |
| `--include-kalshi` | flag | `false` | Include Kalshi cross-platform arbitrage |
| `--live` | flag | `false` | Live mode: stream arb opportunities using WebSocket price data |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Basic usage
polyterm arbitrage

# With min-spread option
polyterm arbitrage --min-spread 0.03

# JSON output
polyterm arbitrage --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- Local SQLite database (`~/.polyterm/data.db`)
- WebSocket real-time feed


## Related Commands

- [Negrisk](negrisk.md)
- [Compare](compare.md)

---

*Source: `polyterm/cli/commands/arbitrage.py`*
