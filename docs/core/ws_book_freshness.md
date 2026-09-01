# WS Book Freshness

> Classify a CLOB WebSocket as live, stale, or REST-fallback. A still book is not live.

## Overview

`polyterm/core/ws_book_freshness.py` is the freeze detector used by `polyterm watch`. CLOB market sockets can stay connected on protocol PING/PONG while `book` / `price_change` events never arrive (see py-clob-client #292 and rs-clob-client-v2 #63). This module does not open sockets. It labels timestamps the caller already observed.

A connected socket without a book tick for `--stale-after` seconds (default 20) is `ws_stale`. The banner is `WS connected, no book ticks`. REST snapshots are labeled `clob_rest` and `live=false`.

## Source

`polyterm/core/ws_book_freshness.py`

## Usage

### CLI

```bash
polyterm watch --market bitcoin --stale-after 20
polyterm watch --market bitcoin --format json --runs 1
```

JSON book objects include `source`, `live`, `ws_connected`, `ws_stale`, and `quality_flags`. When both sides exist they also include `best_bid`, `best_ask`, and `spread` (`best_ask - best_bid`). A missing side is omitted, never zeroed.

### Python

```python
from polyterm.core.ws_book_freshness import BookTickTracker, is_book_tick

tracker = BookTickTracker(stale_after_seconds=20)
tracker.mark_connected(True)
tracker.note_message({"type": "PONG"})  # not a book tick
freshness = tracker.assess(rest_fallback=True, has_rest_book=True)
```

## Public API

| Name | Description |
|------|-------------|
| `BOOK_TICK_TYPES` | `book`, `price_change`, `last_trade_price` |
| `DEFAULT_STALE_AFTER_SECONDS` | `20` |
| `WS_STALE_FLAG` / `WS_STALE_BANNER` | `ws_stale` / `WS connected, no book ticks` |
| `is_book_tick(message)` | True only for book-tick frames |
| `BookTickTracker` | Last-tick clock for one socket |
| `assess_book_freshness(...)` | Pure classifier |
| `BookFreshness.to_dict()` | JSON shape for watch |

`tick_size_change`, `PING`, and `PONG` are not book ticks.

## How It Works

1. The watch loop (or a test) records `ws_connected` and each WS frame.
2. Only `book`, `price_change`, and `last_trade_price` update `last_tick_at`.
3. If a tick arrived within `stale_after_seconds`, the book is `source=clob_ws` and `live=true`.
4. If the socket has been up that long with no tick, `ws_stale=true` and `live=false`.
5. REST fallback is `source=clob_rest`, still `live=false`.

No lag duration is invented. Missing bid/ask are omitted, not zeroed. Spread is only emitted when both sides exist.

## Honesty

| Claim | Reality |
|-------|---------|
| Live book | Recent `book` / `price_change` / `last_trade_price` tick |
| WS connected | Socket looks up; not sufficient for live |
| `ws_stale` | Connected, no book ticks within N seconds |
| REST book | Snapshot labeled `clob_rest`, not live |

## Data Sources

- CLOB WebSocket frames already received by `CLOBClient.listen_orderbook`
- Optional CLOB REST `/book` snapshot supplied by the caller

This module does not call Gamma, Data API, or Statuspage.

## Related

- [Watch loop](watch_loop.md)
- [Watch CLI](../cli/watch.md)
- [Order book](orderbook.md)
- [CLOB client](../api/clob.md)

## Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_ws_book_freshness.py tests/test_core/test_watch_loop.py tests/test_cli/test_watch.py
.venv/bin/polyterm watch --help
```

Unit tests mock timestamps and WS frames. They must not hit the network.

## Documentation Maintenance

This page should stay aligned with `polyterm/core/ws_book_freshness.py`.

When updating this feature:

- Keep PING/PONG distinct from book ticks.
- Do not document a still book as live.
- Run mocked pytest for this module before committing.
