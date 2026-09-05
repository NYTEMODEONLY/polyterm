# Watch Position

> Lagged Data API position for the wallet already configured on this `polyterm watch` session.

## Overview

`polyterm/core/watch_position.py` is the session helper behind the watch header and JSON `position` object. If `wallet.address` is saved in config, watch fetches that wallet's Data API `/positions` (and `/activity` for cashflow P&L) for the watched market. No wallet means the line and JSON key are omitted. This is not a new screen, not a second wallet client, and not live CLOB.

Empty Data API rows are `no position`. Watch does not invent shares, outcomes, or `$0` P&L that look like a book. P&L is the same activity-cashflow path as `polyterm mywallet --pnl` (`replay_cashflow` + open-size mark), never `SUM(cashPnl)`.

## Source

`polyterm/core/watch_position.py`

## Usage

### CLI

```bash
polyterm watch --market bitcoin
polyterm watch --market bitcoin --format json --runs 1
```

The header line appears only when a wallet is already configured (`polyterm mywallet --connect` / `wallet.address` in `~/.polyterm/config.toml`). JSON includes the same object or omits `position` when no wallet.

### Python

```python
from polyterm.core.watch_position import configured_wallet_address, fetch_watch_position

wallet = configured_wallet_address(config)
payload = fetch_watch_position(
    data_api,
    wallet,
    market_data={"conditionId": "0xcond", "slug": "bitcoin-100k"},
    market_query="bitcoin",
)
```

`None` means omit the surface. A labeled dict means the wallet was configured.

## Public API

| Name | Description |
|------|-------------|
| `configured_wallet_address(config)` | Saved view-only address, or `None` |
| `fetch_watch_position(...)` | Lagged position for this market; never raises |
| `watch_position_dashboard_line(payload)` | One header line, or `""` |
| `matching_market_rows(...)` | Keep Data API rows that belong to this market |

## How It Works

1. Read `wallet.address` from config. Missing or blank is `None` (omit).
2. Resolve identifiers from Gamma (`conditionId`, slug, CLOB token IDs).
3. `GET /positions?user={wallet}&market={conditionId}&sizeThreshold=0` through the existing `DataAPIClient` (the same client `PrintScanner` already holds).
4. Keep rows for this market. `size > 0` becomes shares/outcome. Size missing or `<= 0` is not a fake zero.
5. Page `GET /activity?user={wallet}&market={conditionId}&sortDirection=ASC` and reuse `replay_cashflow` / `mark_open_positions`. Empty activity omits `pnl` / `cashflow`.
6. Stamp `source=data_api`, `lag=true`, `lagged=true`, `quality_flags` includes `lagged_data_api`.

Request errors become `position_unavailable`. Watch keeps running. Activity-only failures keep shares and add `cashflow_unavailable`.

## Honesty labels

| Field | Meaning |
|-------|---------|
| omitted `position` | No wallet in config |
| `source` | `data_api` |
| `lag` / `lagged` | `true` |
| `has_position` | `true` only when a row has parseable `size > 0` |
| `shares` / `outcome` | From Data API position rows; omitted when empty |
| `pnl` / `cashflow` | Activity cashflow + open mark when activity exists; omitted otherwise |
| `pnl_source` | `activity-cashflow` when P&L is present |
| `quality_flags` | includes `lagged_data_api`, never `live_data_api_trades` |

Header example with a position: `Wallet: 0x0000…0001 | 120 Yes | cashflow P&L -$60.00 | lagged Data API`.

Empty: `Wallet: 0x0000…0001 | no position | lagged Data API`.

## Data Sources

- Config `wallet.address` (view-only)
- Data API `GET /positions` and `GET /activity` via the existing `DataAPIClient`
- Lag labels from `polyterm/api/data_api_lag.py`
- Cashflow helpers from `polyterm/core/pnl_cashflow.py`

Not used: private keys, order execution, `SUM(cashPnl)`, `makerPnl`, live CLOB, a second wallet HTTP client, `polyterm pnl` local journal.

Identifiers: CLOB condition IDs for the Data API `market=` query. Gamma slugs and CLOB token IDs are matching fallbacks only.

## Related

- [Watch loop](watch_loop.md)
- [Watch CLI](../cli/watch.md)
- [Activity-cashflow P&L](pnl_cashflow.md)
- [Data API client](../api/data_api.md)
- [Data API lag labels](../api/data_api_lag.md)
- [Mywallet CLI](../cli/mywallet.md)

## Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_watch_position.py tests/test_cli/test_watch.py tests/test_cli/test_live_surface_layouts.py tests/test_core/test_watch_loop.py
.venv/bin/polyterm watch --help
.venv/bin/polyterm watch --market bitcoin --format json --runs 1
```

Unit tests mock Data API. They must not hit the network.

## Documentation Maintenance

This page should stay aligned with `polyterm/core/watch_position.py`.

When updating this feature:

- Keep Data API fills lagged. Do not document a live wallet tape.
- Do not document SUM(cashPnl) as watch P&L.
- Empty position stays "no position", never invented zeros.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.
