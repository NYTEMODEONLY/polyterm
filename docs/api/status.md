# StatusPageClient

> Tiny Statuspage v2 client for `status.polymarket.com`. Unreachable pages are `status_unknown`, never operational.

## Overview

`StatusPageClient` fetches the documented Statuspage JSON summary at `https://status.polymarket.com/api/v2/summary.json`. It is a side-channel for incident banners, not a substitute for probing Gamma or CLOB. A failed or unreadable fetch returns `status_unknown`. The client never reports operational unless the payload contains the Statuspage indicator `none`.

This module does not invent Polymarket-specific component names. Component entries are copied from the JSON `components` list when both `name` and `status` are strings.

## Key Classes and Functions

### `StatusPageSnapshot`

Parsed Statuspage v2 summary, or an honest unknown result.

| Field | Type | Description |
|-------|------|-------------|
| `reachable` | `bool` | True when HTTP succeeded enough to parse or reject JSON |
| `indicator` | `str` | `none`, `minor`, `major`, `critical`, `maintenance`, or `status_unknown` |
| `description` | `str` | Statuspage description, or an unknown-page message |
| `page_url` | `str` | Status page URL |
| `page_name` | `str` | Statuspage `page.name` when present |
| `updated_at` | `str` | Statuspage `page.updated_at` when present |
| `components` | `list` | `{name, status}` pairs copied from the payload |
| `error` | `str` or `None` | Failure detail for unknown snapshots |

`to_dict()` returns a JSON-serializable mapping. Unknown snapshots include `error`.

### `StatusPageClient`

HTTP client for the Statuspage summary. Default timeout is 5 seconds. There is no retry loop: a failed fetch is unknown, not delayed operational.

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(base_url=DEFAULT_STATUS_PAGE_URL, timeout=5.0, session=None)` | Optional injected `requests.Session` for tests |
| `get_summary` | `() -> StatusPageSnapshot` | `GET /api/v2/summary.json` |
| `close` | `() -> None` | Close the session when the client created it |

### Helpers

| Function | Description |
|----------|-------------|
| `parse_statuspage_summary(payload, reachable=True, page_url=...)` | Parse a Statuspage v2 summary object |
| `unknown_status_snapshot(reachable, error, ...)` | Build `indicator=status_unknown` |

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `https://status.polymarket.com/api/v2/summary.json` | GET | Documented Statuspage v2 summary (indicator, description, components) |

Statuspage v2 page-level `status.indicator` values:

| Indicator | Meaning |
|-----------|---------|
| `none` | All systems operational |
| `minor` | Minor incident |
| `major` | Major incident |
| `critical` | Critical incident |
| `maintenance` | Maintenance window |

Any other indicator, a non-object payload, missing `status`, HTTP error, timeout, connection failure, or non-JSON body maps to `status_unknown`. The description `All Systems Operational` is never used for those failures.

## Configuration

- **Base URL**: `https://status.polymarket.com` (constructor override for tests)
- **Timeout**: 5 seconds, single attempt
- No API key

## Rate Limiting / Error Handling

- No retries. Status page downtime must surface as `status_unknown`.
- `requests` timeouts and connection errors become unknown snapshots.
- HTTP 4xx/5xx become unknown snapshots with `reachable=False`.
- HTTP 200 with invalid JSON is reachable but still `status_unknown`.

## Data Flow

1. `get_summary()` calls `GET {base}/api/v2/summary.json`.
2. On transport or HTTP failure, return `unknown_status_snapshot`.
3. On JSON success, `parse_statuspage_summary` requires `status.indicator` to be a documented Statuspage value.
4. `indicator == "none"` is the only operational page result.
5. Callers combine this snapshot with live Gamma/CLOB probes in `service_health`.

## External Dependencies

- `requests` -- HTTP client

## Related

- [Service health combiner](../core/service_health.md)
- [Watch](../cli/watch.md)
- [Aggregator](aggregator.md) -- Gamma/CLOB outage honesty for market lists

## Verification

- `tests/test_api/test_status.py` mocks `requests.Session`. Unit tests do not use the live status page.
- `.venv/bin/python -m pytest tests/test_api/test_status.py`
