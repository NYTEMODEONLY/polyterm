# Wallets

> Track and analyze whale and smart money wallets

## Overview

Track and analyze whale and smart money wallets.

## Usage

### CLI

```bash
polyterm wallets [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `11`, `wal`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | ['whales', 'smart', 'suspicious', 'all'] | `whales` | Type of wallets to show |
| `--limit` | int | `20` | Maximum wallets to show |
| `--analyze` | string | `none` | Analyze specific wallet address |
| `--refresh` | flag | `false` | Refresh analyzed wallet from lagged Data API (not live CLOB) |
| `--min-win-rate` | float | `0.70` | Minimum win rate for `--type smart` |
| `--min-trades` | int | `10` | Minimum trade count for `--type smart` |
| `--track` | string | `none` | Add wallet to tracking list |
| `--untrack` | string | `none` | Remove wallet from tracking list |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Basic usage
polyterm wallets

# With type option
polyterm wallets --type whales

# JSON output
polyterm wallets --format json

# Agent-facing local smart-money leaderboard
polyterm wallets --type smart --limit 20 --format json
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for lists and `--analyze` without `--refresh`
- Lagged Data API (`data-api.polymarket.com`) for `--analyze --refresh` wallet, positions, and trades — not live CLOB


## Related Commands

- [Whales](whales.md)
- [Follow](follow.md)
- [Clusters](clusters.md)
- [Attribution](attribution.md)
- [Groups](groups.md)

---

*Source: `polyterm/cli/commands/wallets.py`*

## June 2026 Data API Refresh

`polyterm wallets --analyze <address> --refresh` calls the public Polymarket Data API through `WalletIntelligence`. This produces a richer profile than local SQLite alone. The Data API path is lagged (not live CLOB). Table output shows a lagged banner; JSON includes `lag=true`, `lagged=true`, and `quality_flags` containing `lagged_data_api`.

```bash
polyterm wallets --analyze 0xabc... --refresh --format json
```

The refreshed payload includes positions, recent trades, value data when available, P&L summary, win rate, concentration, top categories, top markets, tags, and quality flags. This remains view-only and no-custody.

## Agent Tool: `wallet.smart_money`

Agents can call `wallet.smart_money` through MCP or the JSON-lines adapter to inspect locally identified high win-rate wallets without touching external state:

```bash
printf '{"tool":"wallet.smart_money","args":{"min_win_rate":0.7,"min_trades":10,"limit":20}}\n' | polyterm agent jsonl-server
```

The tool returns the stable PolyTerm envelope. `data.wallets` preserve the older `edge_score` field and also include `smart_money_score`, `wallet_role`, `is_whale`, `is_noisy`, `noisy_reasons`, `ranking_inputs`, and an `explanation`. Ranking inputs include hit rate, trade count, total volume, largest trade, recency, market focus, wallet risk score, and explicit `realized_pnl_available=false` when local realized PnL is not available.

Quality flags include `local_db_smart_money` and `requires_recent_refresh_for_live_flow`; refresh wallet evidence with `wallet.whales` or `polyterm wallets --analyze <address> --refresh` when recency matters.
