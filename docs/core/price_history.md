# Price History

> CLOB-backed price series builder, plus an opt-in labeled random-walk demo.

## Overview

`polyterm/core/price_history.py` turns CLOB `GET /prices-history` rows into a sorted YES-price series with summary, milestones, and trend. The default CLI/TUI path uses this real series. If CLOB history is missing, callers refuse. A seeded random walk exists only for `--demo` and is labeled `uses_historical_data: false`.

This module does not place trades or access private keys.

## Usage

```python
from polyterm.core.price_history import (
    parse_clob_history_rows,
    build_clob_payload,
    build_demo_payload,
    refuse_payload,
    period_to_hours,
    select_clob_granularity,
    build_time_bounds,
)

hours = period_to_hours("week")
interval, fidelity = select_clob_granularity(hours)
start_ts, end_ts = build_time_bounds(hours)
points = parse_clob_history_rows(raw_rows, start_ts, end_ts)
payload = build_clob_payload(
    points,
    market_title="Example",
    period="week",
    hours=hours,
    token_id="token-yes",
)
assert payload["uses_historical_data"] is True
assert payload["source"] == "clob_prices_history"
```

## Key Functions

| Function | Description |
|----------|-------------|
| `period_to_hours(period)` | Map `day`/`week`/`month`/`all` to a lookback in hours |
| `select_clob_granularity(hours)` | Pick CLOB `interval` and `fidelity` |
| `build_time_bounds(hours)` | Inclusive unix `[start, end]` window |
| `parse_clob_history_rows(history, start_ts, end_ts)` | Keep in-window `{t, p}` rows as sorted points |
| `summarize_series(points, ...)` | High/low/change/volatility/milestones/trend |
| `build_clob_payload(...)` | Success payload with `uses_historical_data: true` |
| `build_demo_payload(...)` | Labeled random walk; not historical |
| `refuse_payload(error)` | `success: false`, `source: none` |

## Return Contract

CLOB success:

| Field | Value |
|-------|-------|
| `success` | `true` |
| `mode` / `source` | `clob_prices_history` |
| `uses_historical_data` | `true` |
| `clob_token_id` | Primary YES CLOB token ID |
| `history.points` | `{timestamp, date, price}` from CLOB |

Demo:

| Field | Value |
|-------|-------|
| `success` | `true` |
| `mode` / `source` | `demo_random_walk` |
| `uses_historical_data` | `false` |
| `disclosure` | Random-walk warning |

Refusal:

| Field | Value |
|-------|-------|
| `success` | `false` |
| `mode` | `unavailable` |
| `source` | `none` |
| `uses_historical_data` | `false` |

`history.summary.reported_volume` is a current Gamma snapshot, not period volume derived from CLOB rows. CLOB `/prices-history` returns `{t, p}` only.

## Granularity

| Hours | `interval` | `fidelity` |
|-------|------------|------------|
| <= 1 | `1h` | 60 |
| <= 6 | `6h` | 60 |
| <= 24 | `1d` | 300 |
| longer | `max` | 3600 |

Period mapping: `day=24`, `week=168`, `month=720`, `all=2160` hours.

## Data Sources

- CLOB REST `GET /prices-history` with `market=<CLOB token ID>`, `interval`, `fidelity`, `startTs`, `endTs`
- Gamma market search only for title, token IDs, and current snapshot fields
- Seeded RNG only on the `--demo` path

## Related

- CLI: [history](../cli/history.md)
- TUI: [history screen](../tui/screens/history.md)
- CLOB client: [clob](../api/clob.md)
- Identifier helpers: [market_utils](../api/market_utils.md)
- Chart (also CLOB-backed): [chart](../cli/chart.md)

## Documentation Maintenance

This page must stay aligned with `polyterm/core/price_history.py`.

When updating this feature:

- Keep CLOB token IDs distinct from Gamma market IDs and CLOB condition IDs.
- Do not describe the demo path as live Polymarket history.
- Run `.venv/bin/python scripts/validate_docs.py` and focused pytest for this module.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- New modules should have a dedicated page rather than relying only on the index.
- Pages that depend on live market data should name Gamma and CLOB as the source.
