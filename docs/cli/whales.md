# Whales

> Track large trades (whale activity)

## Overview

Track large trades (whale activity).

## Usage

### CLI

```bash
polyterm whales [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `3`, `w`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--min-amount` | int | `10000` | Minimum trade size to track |
| `--market` | string | `none` | Filter by market ID |
| `--hours` | int | `24` | Hours of history to check |
| `--limit` | int | `20` | Maximum number of trades to show |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Basic usage
polyterm whales

# With min-amount option
polyterm whales --min-amount 10000

# JSON output
polyterm whales --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Follow](follow.md)
- [Wallets](wallets.md)
- [Clusters](clusters.md)
- [Attribution](attribution.md)
- [Groups](groups.md)

---

*Source: `polyterm/cli/commands/whales.py`*

## June 2026 Wallet-Level Mode

`polyterm whales --wallets` exposes wallet-level whale activity from local trade history. This mode is intended for whale watchers and agents that need wallet addresses instead of only high-volume market proxies.

```bash
polyterm whales --wallets --min-amount 50000 --hours 24 --format json
```

The wallet mode reads local SQLite trades through `WalletIntelligence.local_whales()`. Its JSON output includes wallet address, trade count, notional value, largest trade, top markets, and quality flags. Quality flags may include `local_db_only` and `trade_direction_may_be_inferred`, so agents should treat this as observed local evidence.
