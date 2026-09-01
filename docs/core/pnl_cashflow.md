# Activity-cashflow P&L

> Honest wallet P&L from lagged Data API `/activity` cashflow, not `SUM(cashPnl)`.

## Overview

`polyterm/core/pnl_cashflow.py` replays public Data API activity rows into a signed cashflow, then marks remaining open size from Data API positions. That is the method that still holds when `/positions.cashPnl` drops redeemed winners (a profitable wallet can look like a loss).

Official lb-api `GET /profit` is an optional pre-fee cross-check after June 2026 taker fees. It is never the source of truth. `makerPnl` is not trusted. This module does not invent cash, lag seconds, or a fee gap.

## Source

`polyterm/core/pnl_cashflow.py`

## Usage

### CLI

```bash
polyterm mywallet --pnl --address 0x0000000000000000000000000000000000000001
polyterm mywallet --pnl --address 0x0000000000000000000000000000000000000001 --format json
```

`--format json` does not prompt. The command is view-only and does not use private keys.

`polyterm pnl` stays the local closed-position journal. Do not treat it as Data API P&L.

### Python

```python
from polyterm.core.pnl_cashflow import CashflowPnl, replay_cashflow, mark_open_positions

engine = CashflowPnl(data_api=client)
report = engine.compute("0xabc...")
```

## Public API

| Name | Description |
|------|-------------|
| `classify_activity_type(row)` | Map a row to `buy`/`sell`/`redeem`/`merge`/`split`/`rebate`, or `None` to skip |
| `activity_cash_delta(row)` | Signed USDC from `usdcSize` when the type is known |
| `replay_cashflow(activities)` | Sum signed cashflow; skip unknown and malformed rows |
| `mark_open_positions(positions)` | Open-size mark from `currentValue` or `size * curPrice` |
| `parse_leaderboard_profit(payload)` | Read lb-api `/profit` `amount` when present |
| `build_report(...)` | Stamp `source=activity-cashflow`, `vs-leaderboard=pre-fee`, lag labels |
| `CashflowPnl.compute(address)` | Fetch activity and positions, then assemble the labeled report |

## How It Works

1. Page Data API `GET /activity?user={address}` with `sortDirection=ASC` (MERGE/SPLIT can be empty under DESC).
2. Classify BUY, SELL, TRADE+side, REDEEM, MERGE, SPLIT, REBATE / MAKER_REBATE / TAKER_REBATE.
3. Cash is `usdcSize` only. Missing or unparseable cash skips the row. `size * price` is not used.
4. Signed cashflow: `SELL + REDEEM + MERGE + REBATE - BUY - SPLIT`.
5. Mark remaining size from Data API `/positions` when `currentValue` or `size` and `curPrice` exist. `cashPnl` is not summed.
6. Reported P&L is cashflow plus open mark when both exist. Empty activity is an honest empty payload (`pnl`/`cashflow` null), not a synthetic zero from positions.
7. Optional lb-api `GET /profit?window=all&address=` becomes `leaderboard_profit`. Errors or empty responses are null plus `leaderboard_profit_unavailable`. The gap is not labeled as fees.

Unknown activity types (DEPOSIT, REWARD, CONVERSION, and anything else) do not create cash.

## Honesty labels

Every JSON payload includes:

| Field | Value |
|-------|--------|
| `source` | `activity-cashflow` |
| `vs_leaderboard` / `vs-leaderboard` | `pre-fee` |
| `lag` / `lagged` | `true` (from `data_api_lag`) |
| `quality_flags` | includes `lagged_data_api`, never `live_data_api_trades` |

No lag duration is invented. Table output copies the lagged Data API disclosure.

## Quality flags

| Flag | Meaning |
|------|---------|
| `lagged_data_api` | Data API activity/positions are not live CLOB |
| `empty_activity` | No activity rows; P&L is not synthesized |
| `activity_truncated` | Activity pagination hit the offset cap or a later-page error |
| `open_mark_unavailable` | Positions fetch failed; `open_mark` is null |
| `positions_truncated` | Position pagination hit the offset cap |
| `leaderboard_profit_unavailable` | lb-api `/profit` missing or error |
| `skipped_unknown_activity_types` | Some rows were not BUY/SELL/REDEEM/MERGE/SPLIT/REBATE |
| `skipped_malformed_activity` | Known type but no parseable `usdcSize` |

## Data Sources

- Data API `GET /activity` via `DataAPIClient.get_activity`
- Data API `GET /positions` via `DataAPIClient.get_positions` (`sizeThreshold=0` when paging)
- Optional lb-api `GET https://lb-api.polymarket.com/profit`
- Lag labels from `polyterm/api/data_api_lag.py`

Not used: `SUM(cashPnl)`, `makerPnl`, `DataAPIClient.get_profit_summary`, live CLOB, local SQLite journals, The Graph / Goldsky.

## Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_pnl_cashflow.py tests/test_cli/test_mywallet_pnl.py
.venv/bin/polyterm mywallet --help
.venv/bin/polyterm mywallet --pnl --address 0x0000000000000000000000000000000000000001 --format json
```

Unit tests mock activity streams. They must not hit the network.

## Related

- [Mywallet CLI](../cli/mywallet.md)
- [Local Pnl journal](../cli/pnl.md)
- [Data API client](../api/data_api.md)
- [Data API lag labels](../api/data_api_lag.md)
- [Wallet intelligence](wallet_intelligence.md)

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module.

When updating this feature:

- Confirm `polyterm/core/pnl_cashflow.py` still exists.
- Keep `source=activity-cashflow` and `vs-leaderboard=pre-fee` on JSON and table output.
- Do not document SUM(cashPnl) as wallet P&L.
- Do not document a lag duration.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.
