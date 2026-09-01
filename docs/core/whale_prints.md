# Whale Prints

> Wallet-level whale view from lagged Data API prints. Not insider theater.

## Overview

`polyterm/core/whale_prints.py` is the core behind `polyterm whales --wallets`. It reuses `PrintScanner` and `data_api_lag`. A whale print is a public Data API fill that meets a minimum notional. Those fills are lagged Data API rows. They are not the live CLOB tape.

Empty tape stays empty. The module does not invent wallets, notionals, prices, timestamps, lag duration, 80% win-rate INSIDER flags, syndicate/Louvain clusters, or copy-trade execution.

## Source

`polyterm/core/whale_prints.py`

## Usage

### CLI

```bash
polyterm whales --wallets --min-notional 10000 --format json
polyterm whales --wallets --min-notional 10000 --market bitcoin-100k
polyterm whales --wallets --local --min-amount 50000 --hours 24
```

`--min-notional` is an alias of `--min-amount`. Default `$10,000`, the same print floor as `polyterm watch` and `polyterm alerts --evaluate print`.

`--local` does not use this module. It reads the local observed-trades database through `WalletIntelligence.local_whales`.

### Python

```python
from polyterm.core.print_scanner import PrintScanner
from polyterm.core.whale_prints import scan_whale_prints

payload = scan_whale_prints(
    scanner=PrintScanner(data_api=client),
    min_notional=10000,
    hours=24,
    limit=20,
)
```

## Public API

| Name | Description |
|------|-------------|
| `DEFAULT_PRINT_MIN_NOTIONAL` | `10000.0`, same floor as watch/alerts prints |
| `scan_whale_prints(scanner, min_notional, market, hours, limit, now)` | Fetch lagged prints, optional hours filter, wallet rollup |
| `rollup_prints_by_wallet(prints)` | Aggregate real prints by wallet. Missing wallets are omitted |

## How It Works

1. `PrintScanner.fetch_prints` reads Data API `/trades` (`filterType=CASH` when there is no wallet/market filter).
2. Non-trade activity is skipped. Missing fields are omitted.
3. `match_prints` keeps rows at or above `min_notional`.
4. Optional `--hours` drops prints whose timestamps are older than the window. Unknown timestamps are kept. Timestamps are never invented.
5. Displayed prints are rolled up by wallet address when an address is present.
6. The payload is stamped `source=data_api`, `lag=true`, `lagged=true`. Quality flags include `lagged_data_api` and never `live_data_api_trades`.

`--hours` is a client-side timestamp filter on the recent Data API page. It does not paginate a complete historical tape.

## Honesty

| Claim | Reality |
|-------|---------|
| Wallet-level whale print | Public Data API `/trades` row with a real address when the API sent one |
| Live CLOB fill tape | Not this module |
| Empty tape | `prints=[]`, `wallets=[]` |
| Missing wallet on a print | Omitted from the rollup. Not replaced with `unknown` or a synthetic whale |
| Insider / 80% WR flag | Not computed |
| Syndicate / Louvain / copy | Out of scope |
| Lag duration | Not invented |

This workflow is view-only. It does not write SQLite and does not place orders.

## JSON

`polyterm whales --wallets --format json` includes:

- `mode: "wallet_trades"`
- `source: "data_api"`, `lag: true`, `lagged: true`
- `min_notional`, `hours`, `fetched`, `skipped`, `matched`, `count`
- `prints` — stamped print rows
- `wallets` — rollup of the displayed tape (`address`, `trade_count`, `notional`, `largest_trade`, `top_markets`)
- `quality_flags` containing `lagged_data_api`

It does not include `insider_score`.

## Data Sources

- Data API `GET /trades` via `PrintScanner` / `DataAPIClient`
- Lag labels from `polyterm/api/data_api_lag.py`

Not used: CLOB REST trades, CLOB WebSocket fills, Gamma volume heuristics, `InsiderDetector`, cluster detection, copy-trade execution.

## Related

- [Whales CLI](../cli/whales.md)
- [Print scanner](print_scanner.md)
- [Data API lag labels](../api/data_api_lag.md)
- [Watch CLI](../cli/watch.md)
- [Alerts CLI](../cli/alerts.md)
- [Wallet intelligence](wallet_intelligence.md) (`--local` only)

## Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_whale_prints.py tests/test_cli/test_whales.py tests/test_core/test_print_scanner.py tests/test_api/test_data_api_lag.py tests/test_cli/test_data_api_lag_labels.py
polyterm whales --wallets --help
polyterm whales --wallets --format json
```

Unit tests mock Data API responses. They must not hit the network.

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module.

When updating this feature:

- Confirm `polyterm/core/whale_prints.py` still exists.
- Keep `--wallets` on lagged Data API prints, not live CLOB.
- Do not document insider scoring or copy-execution on this path.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.
