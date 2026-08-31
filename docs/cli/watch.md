# Watch

> Watch specific markets with customizable alerts. Outages are reported as outages.

## Overview

Watch specific markets with customizable alerts. The live mode renders a fixed dashboard with current market state, probability/volume changes, check count, and recent alerts while polling continues.

Before each JSON/scheduled scan, and at the start of live watch, PolyTerm probes Gamma, CLOB, and `status.polymarket.com`. If Gamma and CLOB both fail, watch reports `mode=outage` (same honesty as `APIAggregator`). An unreachable status page is `status_unknown`, never operational.

Live watch can mutate local alert state when thresholds fire. JSON scheduled scans evaluate `AlertEngine.run_once` (Gamma price) and may insert local alerts. Telegram/Discord delivery is a channel label only in this command; this page does not configure bot tokens.

Verified print alerts are not part of watch. Scan lagged Data API fills with `polyterm alerts --evaluate print --min-notional 10000 --format json`.

## Usage

### CLI

```bash
polyterm watch --market bitcoin
polyterm watch --market bitcoin --format json
```

### TUI

In the TUI main menu, use any of these shortcuts: `4`. The TUI launches the same CLI watch command.

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market` | string | `*required*` | Gamma market ID, slug, or search term |
| `--threshold` | float | `10.0` | Probability change threshold (%) |
| `--volume-threshold` | float | `50.0` | Volume change threshold (%) |
| `--interval` | int | `60` | Check interval in seconds |
| `--schedule` | string | `None` | Foreground scan delay, e.g. `15m`, `1h`, `30s` |
| `--runs` | int | `1` | Number of scheduled scans in JSON/scheduled mode |
| `--notify` | string | `None` | Notification channel label, e.g. `telegram` or `discord` |
| `--format` | choice | `table` | `table` or `json` |

## Examples

```bash
# Watch a market search term
polyterm watch --market "bitcoin"

# Tighten probability threshold and refresh interval
polyterm watch --market "bitcoin" --threshold 5 --interval 10

# JSON scan for agents
polyterm watch --market bitcoin --format json

# Scheduled foreground scans
polyterm watch --market bitcoin --schedule 15m --runs 1 --format json
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

## Data Sources

- Gamma Markets REST API (`get_market`, `search_markets`, `get_markets` probe)
- CLOB REST `/sampling-markets` (health probe). CLOB token IDs are required for order books, not for the probe
- Statuspage v2 `GET https://status.polymarket.com/api/v2/summary.json`
- Live snapshots still use Gamma market metadata plus optional CLOB book/ticker

## Related Commands

- [Monitor](monitor.md)
- [Live Monitor](live-monitor.md)
- [Hot](hot.md)
- [Search](search.md)
- [Screener](screener.md)
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

- `tests/test_cli/test_watch.py` and `tests/test_cli/test_live_surface_layouts.py` mock Gamma, CLOB, and the status page.
- `.venv/bin/python -m pytest tests/test_cli/test_watch.py tests/test_api/test_status.py tests/test_core/test_service_health.py`
- `polyterm watch --help`
