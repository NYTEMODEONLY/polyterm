# Print Scanner

> Ingest verified Polymarket prints from lagged Data API trades, not live CLOB.

## Overview

`polyterm/core/print_scanner.py` turns public Data API trade rows into verified prints. A print is a fill that actually happened. The scanner reads `data-api.polymarket.com` through the existing `DataAPIClient`. Those fills are lagged Data API data. They are not the live CLOB tape.

The module never invents wallets, sides, sizes, notionals, prices, timestamps, or a lag duration. Missing fields are omitted. Rows that are not real trades are skipped.

## Source

`polyterm/core/print_scanner.py`

## Usage

### CLI

```bash
polyterm alerts --add-rule print --min-notional 10000 --dry-run --format json
polyterm alerts --evaluate print --min-notional 10000 --format json
polyterm alerts --evaluate print --min-notional 10000 --market bitcoin-100k --wallet 0xabc --dry-run
```

Print evaluation is on `polyterm alerts`, not `polyterm watch`. Watch still evaluates Gamma price rules.

### Python

```python
from polyterm.core.print_scanner import PrintScanner

scanner = PrintScanner(data_api=client)
scan = scanner.scan(min_notional=10000, market="bitcoin-100k")
```

## Public API

| Name | Description |
|------|-------------|
| `PrintScanner.fetch_prints(min_notional, market, wallet, limit)` | Load Data API trade rows, keep real fills, stamp lag labels |
| `PrintScanner.scan(min_notional, market, wallet, limit)` | Fetch then keep prints at or above min notional |
| `normalize_print(raw)` | One row to a lagged print dict, or `None` if it is not a trade |
| `match_prints(prints, min_notional, market, wallet)` | Filter by notional and optional market/wallet |
| `print_message(print_row, min_notional)` | Human text from fields that are present |

## How It Works

1. Global tape uses `DataAPIClient.get_recent_trades`. A wallet or market filter uses `get_trades`.
2. Activity types such as `SPLIT`, `MERGE`, `REDEEM`, and `REWARD` are dropped.
3. A row must look like a fill: size, price, notional, or transaction hash. Otherwise it is skipped.
4. Notional is `size * price` when both are present, else `usdcSize` when present. Unknown notional is omitted and cannot match a min-notional rule.
5. Every kept print is stamped with `source=data_api`, `lag=true`, `lagged=true` via `data_api_lag.stamp`.
6. Empty Data API pages stay empty. Request errors raise. The scanner does not synthesize tape.

Identifiers kept when the API actually sent them: timestamp, wallet, side, size, price, notional, condition ID, market slug, event slug, asset, market ID, title, outcome, transaction hash.

## Honesty

| Claim | Reality |
|-------|---------|
| Verified print | Public Data API `/trades` row |
| Live CLOB fill tape | Not this module |
| Lag duration | Not invented |
| Empty tape | `prints=[]` with `empty_data_api_page` |
| API error | Raised to the caller |

Quality flags always include `lagged_data_api`. They never include `live_data_api_trades`.

## Data Sources

- Data API `GET /trades` via `get_recent_trades` and `get_trades`
- Lag labels from `polyterm/api/data_api_lag.py`

Not used: CLOB REST trades, CLOB WebSocket fills, Gamma volume heuristics.

## Related

- [Alert Engine](alert_engine.md)
- [Alerts CLI](../cli/alerts.md)
- [Data API lag labels](../api/data_api_lag.md)
- [Data API client](../api/data_api.md)
- [Whale tracker](whale_tracker.md)

## Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_print_scanner.py tests/test_core/test_alert_engine.py tests/test_cli/test_alerts.py tests/test_api/test_data_api_lag.py
polyterm alerts --help
polyterm alerts --add-rule print --min-notional 10000 --dry-run --format json
```

Unit tests mock Data API responses. They must not hit the network.

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module.

When updating this feature:

- Confirm `polyterm/core/print_scanner.py` still exists.
- Do not document a lag duration.
- Keep Data API fills distinct from live CLOB.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.
