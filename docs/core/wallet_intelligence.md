# Wallet Intelligence

> Data API and local-state wallet intelligence for smart-money and whale workflows.

## Overview

`polyterm/core/wallet_intelligence.py` builds wallet profiles from public Polymarket Data API surfaces and PolyTerm's local SQLite observations. It is the core module behind refreshed wallet analysis, wallet-level whale output, and future copy-trade controls.

The module is read-only with respect to Polymarket. It may update local wallet rows when refresh data is available so the local database becomes more useful over time.

## Usage

### CLI

```bash
polyterm wallets --analyze 0xabc... --refresh --format json
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
| `local_whales(min_notional, hours)` | Return locally observed wallet-level whale trades. |
| `consensus_moves(trades, min_wallets)` | Find markets where multiple wallets traded together. |

## How It Works

The module calls `DataAPIClient.get_wallet_profile()` for public positions, trades, and wallet value when available. It computes position value, concentration, cash P&L, win rate, total volume, average trade size, largest trade, top categories, and top markets.

Local DB rows are used as a fallback and enrichment source. If refresh data exists, the module upserts a `Wallet` row with volume, win rate, average size, largest trade, and tags such as `whale`, `smart_money`, or `concentrated`.

## Data Sources

- Data API `/positions`
- Data API `/trades`
- Data API `/value` when available
- Local SQLite `wallets` and `trades`

## Quality Flags

Returned profiles include flags such as:

- `partial_data`
- `no_public_positions`
- `no_public_trades`
- `trade_direction_may_be_inferred`
- `local_db_only`

These flags are important for agents because public trade direction and wallet data can be incomplete.

## Agent Notes

Agent tools should call this module through `wallet.inspect` or `wallet.whales`. Mutating behavior is limited to local DB profile refresh. No private keys or authenticated trading credentials are used.

## Verification

```bash
polyterm wallets --analyze 0x0000000000000000000000000000000000000000 --refresh --format json
polyterm whales --wallets --format json
```

Mock Data API responses in focused tests to avoid relying on live wallet availability.

## Related Features

- [Wallets CLI](../cli/wallets.md)
- [Whales CLI](../cli/whales.md)
- [Follow CLI](../cli/follow.md)
- [Data API](../api/data_api.md)
