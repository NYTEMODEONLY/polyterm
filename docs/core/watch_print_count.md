# Watch Print Count

> Session count of lagged Data API prints already on the `polyterm watch` tape.

## Overview

`polyterm/core/watch_print_count.py` counts real lagged Data API prints already shown on this watch session. Traders leave `polyterm watch` open; the header (and JSON) show how many verified prints this process has seen. Empty tape is `0`. The helper does not fetch, does not invent wallets or notionals, and is not a second print scanner.

The count is unique by the same print id watch already uses for notify dedupe (transaction hash, or a row key when hash is missing). Repeats of a fill already shown do not inflate the number.

## Source

`polyterm/core/watch_print_count.py`

## Usage

### CLI

```bash
polyterm watch --market bitcoin
polyterm watch --market bitcoin --format json --runs 1
```

The live header always includes `prints this session: N`. JSON successful scans include `prints.session_count` with the same number.

### Python

```python
from polyterm.core.watch_print_count import (
    WatchPrintSession,
    stamp_session_print_count,
    watch_print_count_dashboard_line,
)

session = WatchPrintSession()
payload = stamp_session_print_count({"prints": rows}, session)
line = watch_print_count_dashboard_line(payload)
```

## Public API

| Name | Description |
|------|-------------|
| `print_rows_from_payload(payload)` | Real print dicts already on the tape; empty is `[]` |
| `payload_print_count(payload)` | `len` of those rows; empty is `0` |
| `WatchPrintSession` | Unique prints seen while this process is open |
| `stamp_session_print_count(payload, session)` | Copy payload and set `session_count` |
| `session_print_count_value(payload)` | Stamped count, else this payload's row count |
| `watch_print_count_dashboard_line(payload)` | `prints this session: N` |

## How It Works

1. Read `prints` from the existing watch payload (`fetch_watch_prints` / `PrintScanner`).
2. Keep dict rows only. Non-dicts and an empty list are not fills.
3. If a `WatchPrintSession` is passed, add each row's print id and stamp `session_count` as the unique total so far.
4. If no session is passed, `session_count` is the unique-or-row count of this payload only (`--runs 1` is that snapshot).
5. The dashboard line is `prints this session: N`. JSON uses the same `session_count`.

Request errors still produce an empty tape (`prints=[]`). The counter stays `0`. Watch does not synthesize rows to make the header look busy.

## Honesty labels

| Field | Meaning |
|-------|---------|
| `prints.session_count` | Unique real lagged prints seen this watch process |
| empty tape | `session_count=0`, `prints=[]` |
| omitted wallets / notionals | Fields stay missing; counting a row does not invent them |

Header example: `prints this session: 3`. Empty: `prints this session: 0`.

## Data Sources

- The existing watch `prints` payload from `PrintScanner` / `fetch_watch_prints`
- Print ids from `watch_loop.print_event_id` (transaction hash when present)

Not used: a second Data API request, CLOB trades, invented wallets, invented notionals, a lag duration.

## Related

- [Watch loop](watch_loop.md)
- [Watch CLI](../cli/watch.md)
- [Print scanner](print_scanner.md)
- [Data API lag labels](../api/data_api_lag.md)

## Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_watch_print_count.py tests/test_cli/test_watch.py tests/test_cli/test_live_surface_layouts.py tests/test_core/test_watch_loop.py
.venv/bin/polyterm watch --help
.venv/bin/polyterm watch --market bitcoin --format json --runs 1
```

Unit tests stub Data API prints. They must not hit the network.

## Documentation Maintenance

This page should stay aligned with `polyterm/core/watch_print_count.py`.

When updating this feature:

- Count only real rows already on the watch tape.
- Empty tape stays `0`, never synthetic fills.
- Do not document a second scanner or a live CLOB tape.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.
