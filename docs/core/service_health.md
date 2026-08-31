# Service Health

> Combine Statuspage, Gamma, and CLOB probes into an honest watch health report.

## Overview

`polyterm/core/service_health.py` is the health combiner for watch. It probes Gamma (`get_markets`) and CLOB (`get_current_markets`) and reads `status.polymarket.com` through `StatusPageClient`. The combiner follows the same honesty rule as `APIAggregator.get_live_markets`: when both live APIs raise, the result is an outage, not an empty market list.

A missing status page is `status_unknown`. Working Gamma and CLOB probes never upgrade an unknown status page to operational.

## Public API

| Function | Description |
|----------|-------------|
| `probe_gamma(gamma_client)` | Call `get_markets(limit=1, active=True, closed=False)`. Exceptions are `ok=False`. Empty success is still ok. |
| `probe_clob(clob_client)` | Call `get_current_markets(limit=1)`. Exceptions are `ok=False`. |
| `combine_health(gamma, clob, status_page)` | Pure combiner used by tests and `assess_service_health` |
| `assess_service_health(gamma_client, clob_client, status_client=None)` | Probe then combine |
| `clob_trading_flags(market)` | Copy CLOB `accepting_orders` when present. Does not invent `cancel_only` or `delayed`. |

### `ServiceHealth`

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `str` | `operational`, `degraded`, `outage`, or `status_unknown` |
| `status` | `str` | Same vocabulary as `mode` for JSON (`status=degraded` on partial failure) |
| `message` | `str` | Human-readable reason |
| `gamma` | `SourceProbe` | Gamma probe result |
| `clob` | `SourceProbe` | CLOB probe result |
| `status_page` | `StatusPageSnapshot` | Parsed or unknown status page |

`to_dict()` is the JSON shape attached to `polyterm watch --format json`.

## Combiner rules

| Gamma | CLOB | Status page | Result |
|-------|------|-------------|--------|
| fail | fail | any | `mode=outage`, `status=outage` |
| fail | ok | any | `mode=degraded`, `status=degraded` |
| ok | fail | any | `mode=degraded`, `status=degraded` |
| ok | ok | `indicator=none` | `operational` |
| ok | ok | `minor` or `maintenance` | `degraded` |
| ok | ok | `major` or `critical` | `outage` |
| ok | ok | unreachable/unreadable | `status_unknown` |

A green status page does not hide Gamma+CLOB failures. An unreachable status page does not claim operational.

## CLOB trading flags

CLOB sampling-markets may include `accepting_orders`. Watch may display that key when the watched market dict already has it.

PolyTerm does **not** invent:

- `cancel_only`
- `delayed`

Those names are omitted unless a future CLOB payload actually includes them. `clob_trading_flags()` only copies `accepting_orders`.

## Data Sources

- Gamma Markets REST: `GET /markets` or `/markets/keyset` via `GammaClient.get_markets`
- CLOB REST: `GET /sampling-markets` via `CLOBClient.get_current_markets`
- Statuspage v2: `GET https://status.polymarket.com/api/v2/summary.json`

Identifiers: Gamma numeric IDs and slugs are not required for the probes. CLOB token IDs are not required for the sampling-markets probe.

## Related

- [Status page client](../api/status.md)
- [Aggregator](../api/aggregator.md)
- [Watch](../cli/watch.md)
- [CLOB](../api/clob.md)

## Verification

- `tests/test_core/test_service_health.py` uses mocks only.
- `.venv/bin/python -m pytest tests/test_core/test_service_health.py tests/test_cli/test_watch.py`

## Documentation Maintenance

This page should stay aligned with `polyterm/core/service_health.py`.

When updating this feature:

- Keep the outage vs empty-list distinction explicit.
- Document Statuspage indicator mapping, not guessed component names.
- Do not document invented CLOB flags.
- Run mocked pytest for this module before committing.
