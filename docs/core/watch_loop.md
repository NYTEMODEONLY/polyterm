# Watch Loop

> Helpers for one `polyterm watch` process: lagged prints, CLOB book, notify events.

## Overview

`polyterm/core/watch_loop.py` is the thin scan helper behind `polyterm watch`. It is not a second process and not `polyterm watchdog`. One watch loop can show:

1. CLOB book from WebSocket ticks, or a labeled REST snapshot
2. Verified lagged Data API prints for the resolved market
3. Notify-worthy events (matched prints and existing price/volume shifts)

Empty Data API tape stays empty. A connected WebSocket with no book ticks is `ws_stale`, not live.

## Source

`polyterm/core/watch_loop.py`

## Usage

### CLI

```bash
polyterm watch --market bitcoin
polyterm watch --market bitcoin --format json --runs 1
polyterm watch --market bitcoin --notify telegram --min-notional 10000 --format json
```

`--min-notional` defaults to `10000`. A saved print rule is not required. `--notify telegram|discord` sends only on verified print matches and threshold events, not every poll.

### Python

```python
from polyterm.core.watch_loop import collect_watch_surfaces, notify_events_from_scan

surfaces = collect_watch_surfaces(
    market="bitcoin",
    gamma_client=gamma,
    clob_client=clob,
    print_scanner=scanner,
    min_notional=10000,
)
events = notify_events_from_scan(surfaces["prints"], shifts=[], min_notional=10000)
```

## Public API

| Name | Description |
|------|-------------|
| `DEFAULT_PRINT_MIN_NOTIONAL` | `10000` |
| `empty_prints_payload()` | Labeled empty tape |
| `fetch_watch_prints(...)` | Data API prints for the resolved market |
| `collect_watch_surfaces(...)` | Prints + book for one scan |
| `WatchBookSession` | Background CLOB WS with REST fallback |
| `notify_events_from_scan(...)` | Print matches and threshold events only |
| `dispatch_watch_notifications(...)` | Telegram/Discord send for those events |

Print identifiers prefer CLOB `conditionId`, then slug, then the trader query. Book token IDs come from Gamma `clobTokenIds`.

## How It Works

1. Resolve Gamma metadata when the caller did not already pass a market dict.
2. Fetch Data API `/trades` through `PrintScanner.fetch_prints`. Stamp `source=data_api`, `lag=true`, `lagged=true`.
3. If a `WatchBookSession` is running, classify ticks with `ws_book_freshness`. Frozen sockets fall back to CLOB REST `/book`.
4. JSON scheduled scans skip WS and use REST, labeled `clob_rest`.
5. Notify dedupes on transaction hash (or a row key when hash is missing). Empty polls send nothing.

Request errors become `prints_unavailable` or `rest_error`. They do not become synthetic fills or a live book.

## Honesty labels

| Field | Meaning |
|-------|---------|
| `prints.source` | `data_api` |
| `prints.lag` / `prints.lagged` | `true` |
| `prints.quality_flags` | includes `lagged_data_api`, never `live_data_api_trades` |
| `book.source` | `clob_ws`, `clob_rest`, or `none` |
| `book.live` | `true` only after a recent book tick |
| `book.ws_stale` | Connected WS, no book ticks within N seconds |
| `book.best_bid` / `book.best_ask` | Top of the labeled snapshot. Missing sides stay omitted, never `0` |
| `book.spread` | `best_ask - best_bid` when both sides exist; omitted otherwise |
| `book.best_bid_size` / `book.best_ask_size` | Size at the best level when the snapshot already includes it |

## Data Sources

- Gamma market metadata (`conditionId`, `slug`, `clobTokenIds`)
- Data API trades via `PrintScanner` / `data_api_lag`
- CLOB WS market channel and CLOB REST `/book`

Not used: private keys, order execution, copy-trade, `polyterm watchdog` as a second command.

## Related

- [WS book freshness](ws_book_freshness.md)
- [Print scanner](print_scanner.md)
- [Service health](service_health.md)
- [Watch CLI](../cli/watch.md)
- [Notifications](notifications.md)

## Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_watch_loop.py tests/test_cli/test_watch.py tests/test_core/test_print_scanner.py tests/test_core/test_service_health.py
.venv/bin/polyterm watch --market bitcoin --format json --runs 1
```

Unit tests mock Data API, CLOB REST, and WS frames. They must not hit the network.

## Documentation Maintenance

This page should stay aligned with `polyterm/core/watch_loop.py`.

When updating this feature:

- Keep prints lagged. Do not document a live Data API tape.
- Keep REST books labeled REST.
- Do not add a second user-facing watchdog command from this module.
