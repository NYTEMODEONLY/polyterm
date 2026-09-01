# Watch

> One live session: CLOB book, lagged Data API prints, and an honest outage line.

## Overview

`polyterm watch` is the no-keys session traders leave running on one market. The live dashboard polls Gamma, shows CLOB top-of-book (WebSocket ticks or a labeled REST snapshot), lists recent verified Data API prints, and keeps the Statuspage outage line.

A connected CLOB WebSocket with no `book` / `price_change` ticks is not live. After `--stale-after` seconds (default 20) watch sets `ws_stale` and the banner `WS connected, no book ticks`. REST fallback is allowed when it is labeled `clob_rest`.

Prints are lagged Data API fills (`source=data_api`, `lag=true`). Empty tape stays empty. Watch never invents wallets, notionals, or a lag duration.

`--notify telegram|discord` sends only on verified print matches (default min-notional `$10,000`, no saved print rule required) and on existing price/volume threshold events. It does not fire on every poll.

Before each JSON/scheduled scan, and at the start of live watch, PolyTerm probes Gamma, CLOB, and `status.polymarket.com`. If Gamma and CLOB both fail, watch reports `mode=outage`. An unreachable status page is `status_unknown`, never operational.

Live watch can mutate local alert state when thresholds fire. JSON scheduled scans evaluate `AlertEngine.run_once` (Gamma price) and attach prints + book. Telegram/Discord delivery uses configured bot token / webhook; this page does not store secrets.

This command does not use private keys and does not place orders. It does not spawn `polyterm watchdog`.

## Usage

### CLI

```bash
polyterm watch --market bitcoin
polyterm watch --market bitcoin --format json --runs 1
polyterm watch --market bitcoin --notify telegram --min-notional 10000
```

### TUI

In the TUI main menu, use any of these shortcuts: `4`. The TUI launches the same CLI watch command.

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market` | string | `*required*` | Gamma market ID, slug, or search term |
| `--threshold` | float | `10.0` | Probability change threshold (%) |
| `--volume-threshold` | float | `50.0` | Volume change threshold (%) |
| `--interval` | int | `60` | Check interval in seconds (prints/Gamma). Book freshness is checked every second in live mode |
| `--schedule` | string | `None` | Foreground scan delay, e.g. `15m`, `1h`, `30s` |
| `--runs` | int | `1` | Number of scheduled scans in JSON/scheduled mode |
| `--notify` | string | `None` | `telegram` or `discord`. Sends only on verified prints and threshold events |
| `--min-notional` | float | `10000` | Minimum lagged print notional to notify on. No saved print rule required |
| `--stale-after` | int | `20` | Seconds without book/price_change ticks before `ws_stale` |
| `--format` | choice | `table` | `table` or `json` |

## Examples

```bash
# Live dashboard (Ctrl+C to stop)
polyterm watch --market bitcoin

# Tighten probability threshold and Gamma/print interval
polyterm watch --market bitcoin --threshold 5 --interval 10 --stale-after 20

# JSON scan for agents (REST book + lagged prints)
polyterm watch --market bitcoin --format json --runs 1

# Notify only on verified prints / threshold events
polyterm watch --market bitcoin --notify telegram --min-notional 10000 --format json
```

## Outage and degraded JSON

`--format json` always includes `mode` and `status`.

| Condition | `success` | `mode` | `status` |
|-----------|-----------|--------|----------|
| Gamma and CLOB both raise | `false` | `outage` | `outage` |
| One of Gamma/CLOB raises | depends | `degraded` | `degraded` |
| Both APIs ok, status page unreachable | `true` | `status_unknown` | `status_unknown` |
| Both APIs ok, Statuspage `indicator=none` | `true` | `operational` | `operational` |

Gamma-down / CLOB-up is `status=degraded` and does not call the Gamma-only scan engine. Table mode prints `Watch outage:` instead of `No markets found`.

CLOB `accepting_orders` is forwarded when that key is already on a CLOB market dict. Watch does not invent `cancel_only` or `delayed`.

## Book and prints JSON

Successful scans include `prints` and `book` on each result.

| Field | Meaning |
|-------|---------|
| `prints.source` | `data_api` |
| `prints.lag` / `prints.lagged` | `true` |
| `prints.quality_flags` | includes `lagged_data_api`, never `live_data_api_trades` |
| `prints.prints` | Verified fill rows, or `[]` |
| `book.source` | `clob_ws`, `clob_rest`, or `none` |
| `book.live` | `true` only after a recent book tick |
| `book.ws_stale` | Connected WS, no book ticks within `--stale-after` |
| `book.banner` | `WS connected, no book ticks` when stale |

JSON `--runs 1` uses CLOB REST for the book snapshot (`source=clob_rest`, `live=false`). Live table mode starts the CLOB WebSocket and falls back to REST if ticks freeze.

## Data Sources

- Gamma Markets REST API (`get_market`, `search_markets`, `get_markets` probe)
- CLOB REST `/sampling-markets` (health probe) and `/book` (REST snapshot). CLOB token IDs from Gamma `clobTokenIds`
- CLOB WebSocket market channel (`book`, `price_change`, `last_trade_price`)
- Data API `/trades` via `PrintScanner` (lagged fills, not live CLOB)
- Statuspage v2 `GET https://status.polymarket.com/api/v2/summary.json`

Identifiers: Gamma numeric IDs and slugs resolve the market. Prints prefer CLOB condition IDs. Order books require CLOB token IDs.

## Related Commands

- [Alerts](alerts.md) (`--evaluate print` still exists for one-shot print scans)
- [Orderbook](orderbook.md)
- [Monitor](monitor.md)
- [Live Monitor](live-monitor.md)
- [Watch loop](../core/watch_loop.md)
- [WS book freshness](../core/ws_book_freshness.md)
- [Print scanner](../core/print_scanner.md)
- [Service health](../core/service_health.md)
- [Status page client](../api/status.md)

---

*Source: `polyterm/cli/commands/watch.py`*

## June 2026 Scheduled Agent Mode

`polyterm watch` supports scheduled foreground scans with JSON output.

```bash
polyterm watch --market bitcoin --format json
polyterm watch --market bitcoin --schedule 15m --runs 1 --notify telegram --format json
```

Scheduled mode avoids interactive market selection and returns scan results as JSON. The command is marked long-running in the agent manifest when `--schedule` is used. Outage payloads set `success=false` and `mode=outage` rather than a successful empty `results` list.

## Verification

- `tests/test_cli/test_watch.py` and `tests/test_cli/test_live_surface_layouts.py` mock Gamma, CLOB, Data API prints, and the status page.
- `.venv/bin/python -m pytest tests/test_cli/test_watch.py tests/test_core/test_watch_loop.py tests/test_core/test_ws_book_freshness.py tests/test_core/test_print_scanner.py tests/test_core/test_service_health.py`
- `polyterm watch --help`
- `polyterm watch --market bitcoin --format json --runs 1`
