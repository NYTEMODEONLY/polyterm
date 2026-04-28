# GammaClient

> Gamma Markets REST API client with shared cross-process rate limiting.

## Overview

The `GammaClient` class is the primary API client for Polymarket market data. It provides access to the Gamma REST API for listing markets, searching, fetching prices, volume, trades, liquidity, and resolution data. In `0.9.1`, market listing uses the current `/markets/keyset` endpoint by default because legacy `/markets` offset pagination is deprecated. All requests pass through a `SharedRateLimiter` that coordinates rate limits across concurrent PolyTerm processes using file-based locking. The module also includes a per-process `RateLimiter` fallback.

## Key Classes and Functions

### `RateLimiter`

Simple per-process rate limiter using time-based throttling.

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(requests_per_minute: int = 60)` | Initialize with rate limit; computes `min_interval` as `60.0 / requests_per_minute` |
| `wait_if_needed` | `() -> None` | Sleep if the minimum interval since the last request has not elapsed |

### `SharedRateLimiter`

Cross-process rate limiter using file-based coordination via `fcntl` file locks.

#### Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `requests_per_minute` | `int` | `60` | Maximum requests per minute across all processes |
| `lock_dir` | `Optional[str]` | `None` (defaults to `~/.polyterm`) | Directory for the lock file |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `wait_if_needed` | `() -> None` | Coordinate wait across processes; falls back to per-process limiter on error |

#### Internal Details

- **Lock file**: `~/.polyterm/gamma_rate.lock`
- **Stale threshold**: 120 seconds -- timestamps older than this are discarded (handles crashed processes)
- **Mechanism**: Acquires exclusive `fcntl.LOCK_EX` lock, reads last request timestamp, computes next allowed slot, writes new timestamp, releases lock, then sleeps outside the lock
- **Fallback**: Falls back to per-process `RateLimiter` on Windows (no `fcntl`) or permission errors

### `GammaClient`

Client for the Gamma Markets REST API.

#### Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | `"https://gamma-api.polymarket.com"` | Gamma API base URL |
| `api_key` | `str` | `""` | Optional API key (sets `Authorization: Bearer` header) |

#### Market Data Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_markets` | `(limit: int = 100, offset: int = 0, active: Optional[bool] = None, closed: Optional[bool] = None, tag: Optional[str] = None, market_id: Optional[str] = None) -> List[Dict[str, Any]]` | List markets with filtering via keyset pagination. Defaults to active, non-closed; keeps list-shaped return values for callers |
| `get_market` | `(market_id: str) -> Dict[str, Any]` | Get single market details by ID or slug |
| `get_market_prices` | `(market_id: str) -> Dict[str, Any]` | Get current prices and probabilities |
| `get_market_volume` | `(market_id: str, interval: str = "1h") -> List[Dict[str, Any]]` | Get volume data at specified interval |
| `get_market_trades` | `(market_id: str, limit: int = 100, before: Optional[int] = None) -> List[Dict[str, Any]]` | Get recent trades for a market |
| `get_market_liquidity` | `(market_id: str) -> Dict[str, Any]` | Get liquidity information |
| `search_markets` | `(query: str, limit: int = 20) -> List[Dict[str, Any]]` | Search markets by text query with local fallback |
| `get_trending_markets` | `(limit: int = 10) -> List[Dict[str, Any]]` | Get markets sorted by 24hr volume descending |

#### Resolution Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_resolution` | `(market_id: str) -> Optional[Dict[str, Any]]` | Get resolution/settlement data for a single market |
| `get_resolved_markets` | `(limit: int = 50) -> List[Dict[str, Any]]` | Get recently resolved markets with resolution data |

#### Freshness / Filtering Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `is_market_fresh` | `(market: Dict[str, Any], max_age_hours: int = 24) -> bool` | Check if market data is fresh using active/closed flags or end date |
| `filter_fresh_markets` | `(markets: List[Dict[str, Any]], max_age_hours: int = 24, require_volume: bool = True, min_volume: float = 0.01) -> List[Dict[str, Any]]` | Filter to only fresh, active markets with optional volume threshold |

#### Lifecycle Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `close` | `() -> None` | Close the HTTP session |

## API Endpoints Used

All endpoints are on `https://gamma-api.polymarket.com`:

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/markets/keyset` | GET | `limit`, `next_cursor`, `active`, `closed`, `tag`, `order`, `ascending` | Current market listing endpoint with keyset pagination |
| `/markets` | GET | `limit`, `offset`, `active`, `closed`, `tag`, `order`, `ascending` | Deprecated legacy fallback only when keyset is unavailable |
| `/markets/{market_id}` | GET | -- | Single market details |
| `/markets/{market_id}/prices` | GET | -- | Current prices and probabilities |
| `/markets/{market_id}/volume` | GET | `interval` | Volume data at interval (1m, 5m, 15m, 1h, 4h, 1d) |
| `/markets/{market_id}/trades` | GET | `limit`, `before` | Recent trades |
| `/markets/{market_id}/liquidity` | GET | -- | Liquidity information |
| `/markets/search` | GET | `q`, `limit` | Text search (may return 422 in some environments; has local fallback) |

## Configuration

- **Rate limit**: 60 requests per minute (default), shared across all PolyTerm processes
- **Lock file location**: `~/.polyterm/gamma_rate.lock`
- **Request timeout**: 15 seconds
- **API key**: Optional; set via constructor parameter

## Rate Limiting / Error Handling

### SharedRateLimiter

- File-lock-based coordination at `~/.polyterm/gamma_rate.lock`
- Default: 60 requests per minute across all concurrent PolyTerm processes
- Stale timestamp cleanup: timestamps older than 120 seconds are discarded
- Falls back to per-process `RateLimiter` on Windows or permission errors
- Sleep occurs outside the lock so other processes can reserve their slots

### REST Retry Logic

The `_request` method implements exponential backoff:

| Condition | Behavior |
|-----------|----------|
| HTTP 429 (rate limited) | Wait `min(2^attempt * 2, 30)` seconds; respects `Retry-After` header (capped at 60s) |
| HTTP 5xx (server error) | Wait `2^attempt` seconds, retry up to `retries - 1` times |
| Timeout | Wait `2^attempt` seconds, retry; raise with descriptive message on final attempt |
| Connection error | Wait `2^attempt` seconds, retry; raise with descriptive message on final attempt |
| Other `RequestException` | Raise immediately with no retry |

### Search Endpoint Fallback

`search_markets` tries the `/markets/search` endpoint first. If it receives a 422 or 404 error, it sets `_search_endpoint_supported = False` and falls back to fetching 200 markets via `get_markets` and filtering locally by title substring match.

### Resolution Parsing

`_parse_resolution` determines market outcome from `outcomePrices`:
- A market is "resolved" when closed and one outcome price is >= 0.95
- Status values: `"Resolved: YES"`, `"Resolved: NO"`, `"Pending resolution"`, `"Closed"`, `"Active"`

## Data Flow

1. All REST calls go through `_request` which applies the `SharedRateLimiter` before each HTTP request.
2. `get_markets` returns raw market dicts from `/markets/keyset`, unwrapping the API's `{markets, next_cursor}` response into the legacy list shape expected by PolyTerm tools.
3. `filter_fresh_markets` applies freshness checks using `is_market_fresh` (prefers `active`/`closed` flags, falls back to date parsing).
4. `get_resolution` fetches a single market and parses resolution status from `outcomePrices` and `closed`/`active` flags.
5. `get_resolved_markets` fetches closed markets ordered by end date and attaches `_resolution` data to each.

## External Dependencies

- `requests` -- HTTP client
- `python-dateutil` (optional) -- date parsing for freshness checks; guarded by `HAS_DATEUTIL` flag

## Related

- **CLI commands**: Used by nearly every CLI command as the primary market data source, including: `monitor`, `whales`, `arbitrage`, `predict`, `risk`, `calendar`, `chart`, `compare`, `search`, `stats`, `crypto15m`, `mywallet`, `quicktrade`, `negrisk`, `dashboard`, `fees`, `bookmarks`, `recent`, `pricealert`, `depth`, `hot`, `analytics`, `portfolio`, `trade`, `watch`, and many more
- **TUI screens**: `analytics.py`, `market_picker.py`, `live_monitor.py`
- **Core modules**: `core/scanner.py`, `core/whale_tracker.py` (indirectly), `core/arbitrage.py`, `core/negrisk.py`, `core/predictions.py` (indirectly), `core/historical.py`, `core/analytics.py`, `core/correlation.py`, `core/portfolio.py`
- **Aggregator**: `APIAggregator` uses `GammaClient` as its primary data source
