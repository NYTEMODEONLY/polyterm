# Data API lag labels

> Shared labels that mark Data API wallet, positions, activity, and trades as lagged, not live CLOB.

## Overview

Polymarket Data API wallet, positions, activity, and trades are not the live CLOB fill tape. CLI, TUI, and JSON surfaces that show those rows must say so explicitly. This module is the single source for that label.

It does not invent a lag duration. There is no minutes/seconds field and no estimated delay.

## Source

`polyterm/api/data_api_lag.py`

## Public API

| Name | Description |
|------|-------------|
| `SOURCE` | Canonical JSON source string: `data_api` |
| `LAGGED` | Always `True` |
| `QUALITY_FLAG` | `lagged_data_api` |
| `DISCLOSURE` | Human banner: lagged Data API, not live CLOB |
| `metadata()` | `{source, lag, lagged}` |
| `stamp(payload)` | Add `lag=true` and `lagged=true`; fill `source` when missing |
| `with_quality_flag(flags)` | Prepend `lagged_data_api`; drop the `live_data_api_trades` misnomer |
| `label_payload(payload)` | Stamp lag fields and attach the quality flag |
| `table_title(title)` | Append `— lagged Data API (not live CLOB)` |

`stamp()` leaves nested `source` maps intact so wallet-profile provenance (`positions` / `trades` / `local_wallet`) is not overwritten.

## What Gets Labeled

| Surface | How the label appears |
|---------|------------------------|
| JSON | `source=data_api` (when missing), `lag=true`, `lagged=true`, `quality_flags` includes `lagged_data_api` |
| CLI table | Yellow banner with `DISCLOSURE` plus lagged table title |
| TUI | Panel text on wallets, whales (`--wallets` note), and portfolio screens |
| Print alerts | `polyterm alerts --add-rule print` / `--evaluate print` JSON and table titles |

This is a view-only honesty label. It does not change which API is called.

## What It Does Not Cover

- Live CLOB trades, order books, or WebSocket fills
- Gamma 24h volume heuristics (`polyterm whales` default / `--volume`)
- Local SQLite wallet lists (`polyterm wallets` without `--refresh`, `whales --local`)
- Leaderboard rankings (`/v1/leaderboard`) — those are not fills

## Data Sources

This module does not fetch data. It labels payloads that already came from:

- Data API `/positions`
- Data API `/activity`
- Data API `/trades`
- Data API wallet profile aggregation (`get_wallet_profile`)

Versus live CLOB REST/WebSocket at `clob.polymarket.com`.

## Verification

```bash
.venv/bin/python -m pytest tests/test_api/test_data_api_lag.py tests/test_cli/test_data_api_lag_labels.py
polyterm wallets --help
polyterm whales --help
polyterm portfolio --help
```

Unit tests mock Data API clients. They must not hit the network.

## Related

- [Data API client](data_api.md)
- [CLOB client](clob.md)
- [Wallets CLI](../cli/wallets.md)
- [Whales CLI](../cli/whales.md)
- [Portfolio CLI](../cli/portfolio.md)
- [Alerts CLI](../cli/alerts.md)
- [Print scanner](../core/print_scanner.md)
- [Wallet intelligence](../core/wallet_intelligence.md)

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module.

When updating this feature:

- Confirm `polyterm/api/data_api_lag.py` still exists.
- Do not document a lag duration.
- Keep Data API fills distinct from live CLOB.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.
