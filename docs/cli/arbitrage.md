# Arbitrage

> Scan for arbitrage opportunities across markets

## Overview

Scan for arbitrage opportunities across markets. Live mode uses CLOB WebSocket-fed prices where available and renders in a fixed screen with scan status and opportunity table.

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

# Live WebSocket-fed scanner
polyterm arbitrage --live --min-spread 0.025

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

## June 2026 Cross-Venue Monitor

`polyterm arbitrage` includes a cross-venue hedge monitor branch.

```bash
polyterm arbitrage --venues polymarket,kalshi --query bitcoin --format json
polyterm arbitrage --venues polymarket,kalshi --query election
```

Cross-venue output includes Polymarket market data, external venue data, spread, match confidence, fee-adjusted spread, and quality flags such as `manual_review_match`. Agents should treat low-confidence matches as research leads because venue identifiers are not interchangeable.
