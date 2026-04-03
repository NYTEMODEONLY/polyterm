# APIAggregator

> Multi-source data aggregation with automatic fallback between Gamma and CLOB APIs.

## Overview

The `APIAggregator` class provides a unified interface for fetching market data from multiple Polymarket API sources. It tries the Gamma API first (which includes volume data) and falls back to the CLOB API if Gamma is unavailable. It also supports enriching market data by combining information from both sources and validating data freshness.

## Key Classes and Functions

### `APIAggregator`

Aggregates data from multiple Polymarket API sources with fallback. Requires both a `GammaClient` and `CLOBClient` instance, using Gamma as the primary source and CLOB as the fallback.

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(gamma_client: GammaClient, clob_client: CLOBClient)` | Initialize with both API clients |
| `get_live_markets` | `(limit: int = 100, require_volume: bool = True, min_volume: float = 0.01) -> List[Dict[str, Any]]` | Get live markets with automatic Gamma-to-CLOB fallback |
| `enrich_market_data` | `(market_id: str, base_data: Dict[str, Any]) -> Dict[str, Any]` | Enrich a market dict by adding volume from Gamma and order book data from CLOB |
| `get_top_markets_by_volume` | `(limit: int = 10, min_volume: float = 100) -> List[Dict[str, Any]]` | Get top markets sorted by 24hr volume |
| `validate_data_freshness` | `(markets: List[Dict[str, Any]]) -> Dict[str, Any]` | Validate freshness of market data and produce a report |

## API Endpoints Used

The aggregator does not call endpoints directly. It delegates to its constituent clients:

| Client | Endpoint | Method | Used By |
|--------|----------|--------|---------|
| `GammaClient` | `/markets` | GET | `get_live_markets`, `enrich_market_data` |
| `CLOBClient` | `/sampling-markets` | GET | `get_live_markets` (fallback) |
| `CLOBClient` | `/book` | GET | `enrich_market_data` |

## Configuration

No dedicated configuration. Behavior is determined by the `GammaClient` and `CLOBClient` instances passed to the constructor. Both clients carry their own rate limiting and retry settings.

## Rate Limiting / Error Handling

- **Fallback pattern**: `get_live_markets` tries Gamma first. If Gamma raises any exception or returns no fresh markets, it falls back to CLOB. If both fail, it returns an empty list.
- **Enrichment failures are silent**: `enrich_market_data` wraps each data-source call in a bare `except Exception: pass`, so missing enrichment data never causes an error.
- **Data source metadata**: Enriched market dicts include a `_data_sources` list (e.g., `['gamma', 'clob']`) indicating which sources contributed data.

## Data Flow

1. `get_live_markets` calls `GammaClient.get_markets()` and filters with `filter_fresh_markets()`.
2. If Gamma fails or returns nothing, it calls `CLOBClient.get_current_markets()` and filters with `is_market_current()`.
3. `get_top_markets_by_volume` fetches up to 5x the requested limit (minimum 100) via `get_live_markets`, then sorts by `volume24hr` descending.
4. `enrich_market_data` takes existing market data and optionally adds `volume`, `volume24hr`, `order_book`, and `spread` fields.
5. `validate_data_freshness` iterates markets and produces a report with counts of fresh/stale markets, volume coverage, and warning messages.

## External Dependencies

- `polyterm.api.gamma.GammaClient` -- primary data source
- `polyterm.api.clob.CLOBClient` -- fallback data source

## Related

- **CLI commands**: `monitor`, `live_monitor`, `analytics` (all import `APIAggregator`)
- **TUI screens**: `analytics.py` (uses `get_top_markets_by_volume` directly for trending markets display), `market_picker.py` (uses aggregator for market selection)
- **Core modules**: `core/scanner.py` (uses aggregator for market monitoring and shift detection)
