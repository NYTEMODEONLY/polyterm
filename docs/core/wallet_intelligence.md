# Wallet Intelligence

> Data API and local-state wallet intelligence for smart-money and whale workflows.

## Overview

`polyterm/core/wallet_intelligence.py` builds wallet profiles from public Polymarket Data API surfaces and PolyTerm's local SQLite observations. It is the core module behind refreshed wallet analysis, wallet-level whale output, and future copy-trade controls.

The module is read-only with respect to Polymarket. It may update local wallet rows when refresh data is available so the local database becomes more useful over time.

## Usage

### CLI

```bash
polyterm wallets --analyze 0xabc... --refresh --format json
polyterm wallets --type smart --format json
polyterm whales --wallets --format json
```

### Python

```python
from polyterm.core.wallet_intelligence import WalletIntelligence

engine = WalletIntelligence()
profile = engine.analyze_wallet("0xabc...", refresh=True)
```

## Public API

| Method | Description |
|--------|-------------|
| `analyze_wallet(address, limit, refresh)` | Build a wallet profile from Data API and local state. |
| `smart_money(min_win_rate, min_trades, limit)` | Return locally identified high win-rate wallets ranked by edge score. |
| `live_whales(min_notional, hours, limit, market)` | Return Data API whale trades and wallet rollups for agent questions. |
| `local_whales(min_notional, hours)` | Return locally observed wallet-level whale trades. |
| `consensus_moves(trades, min_wallets)` | Find markets where multiple wallets traded together. |

## How It Works

The module calls `DataAPIClient.get_wallet_profile()` for public positions, trades, and wallet value when available. It computes position value, concentration, cash P&L, win rate, total volume, average trade size, largest trade, top categories, and top markets.

Local DB rows are used as a fallback and enrichment source. If refresh data exists, the module upserts a `Wallet` row with volume, win rate, average size, largest trade, and tags such as `whale`, `smart_money`, or `concentrated`.

`smart_money()` reads the local wallet table through `Database.get_smart_money_wallets()`, applies caller thresholds, and ranks qualifying wallets by `edge_score` (win rate multiplied by capped trade-count depth). This is intentionally local-only; agents should refresh wallet or whale evidence before treating the leaderboard as live flow.

`live_whales()` also logs the Data API whale-query result set locally: it upserts whale wallet summaries into `wallets` and inserts each matching public trade into `trades`. Trade caching is idempotent when a transaction hash is available, keyed by transaction hash + wallet + market, so repeated natural-language lookups enrich the local store without duplicating rows.

Data API wallet, positions, and trades returned by `analyze_wallet` (refresh path), `live_whales`, and `whale_trades` are lagged. They are not the live CLOB tape. Payloads include `lag=true`, `lagged=true`, and `quality_flags` containing `lagged_data_api`. Do not invent a lag duration.

## Data Sources

- Data API `/positions`
- Data API `/trades`
- Data API `/trades?filterType=CASH&filterAmount=<min_notional>` for lagged whale discovery (not live CLOB)
- Data API `/value` when available
- Local SQLite `wallets` and `trades`

## Quality Flags

Returned profiles include flags such as:

- `partial_data`
- `no_public_positions`
- `no_public_trades`
- `trade_direction_may_be_inferred`
- `lagged_data_api`
- `public_data_api`
- `data_api_recent_tape_window_limited`
- `local_db_only`
- `local_db_smart_money`
- `requires_recent_refresh_for_live_flow`

These flags are important for agents because public trade direction and wallet data can be incomplete.

## Agent Notes

Agent tools should call this module through `wallet.inspect`, `wallet.whales`, or `wallet.smart_money`. Mutating behavior is limited to local DB profile refresh. No private keys or authenticated trading credentials are used.

## Verification

```bash
polyterm wallets --analyze 0x0000000000000000000000000000000000000000 --refresh --format json
polyterm wallets --type smart --format json
printf '{"tool":"wallet.smart_money","args":{"limit":5}}\n' | polyterm agent jsonl-server
polyterm whales --wallets --format json
```

Mock Data API responses in focused tests to avoid relying on live wallet availability.

## Related Features

- [Wallets CLI](../cli/wallets.md)
- [Whales CLI](../cli/whales.md)
- [Follow CLI](../cli/follow.md)
- [Data API](../api/data_api.md)
