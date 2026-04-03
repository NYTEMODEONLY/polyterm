# Scanner

> Market monitoring and shift detection engine with multi-source data aggregation.

## Overview

The scanner module continuously monitors Polymarket markets for significant changes in probability, volume, and liquidity. It aggregates data from both Gamma REST API and CLOB endpoints, stores point-in-time snapshots, and fires callbacks when shifts exceed configurable thresholds. It supports both single-market and all-active-market scanning with concurrent execution.

## Key Classes and Functions

### `MarketScanner`

The primary scanner that monitors markets and detects shifts.

#### Constructor

```python
MarketScanner(
    gamma_client: GammaClient,
    clob_client: CLOBClient,
    check_interval: int = 60,
)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_market_snapshot` | `(market_id: str) -> Optional[MarketSnapshot]` | Fetch aggregated snapshot from Gamma + CLOB |
| `store_snapshot` | `(snapshot: MarketSnapshot) -> None` | Store snapshot with history limit |
| `detect_shift` | `(current: MarketSnapshot, previous: Optional[MarketSnapshot], thresholds: Dict[str, float]) -> Optional[Dict]` | Check if changes exceed thresholds |
| `scan_market` | `(market_id: str, thresholds: Dict[str, float]) -> Optional[Dict]` | Scan a single market for shifts |
| `scan_markets` | `(market_ids: List[str], thresholds: Dict[str, float]) -> List[Dict]` | Scan multiple markets concurrently via thread pool |
| `scan_all_active_markets` | `(thresholds: Dict[str, float]) -> List[Dict]` | Scan all active markets using aggregator with data validation |
| `start_monitoring` | `(market_ids: List[str], thresholds: Dict[str, float]) -> None` | Start continuous monitoring loop (blocking) |
| `stop_monitoring` | `() -> None` | Stop the monitoring loop |
| `add_shift_callback` | `(callback: Callable) -> None` | Register callback for shift events |
| `get_market_history` | `(market_id: str, hours: int = 24) -> List[MarketSnapshot]` | Get stored historical snapshots |
| `calculate_volatility` | `(market_id: str, window: int = 10) -> float` | Calculate standard deviation of probability changes |

### `MarketSnapshot`

Point-in-time snapshot of market data.

#### Constructor

```python
MarketSnapshot(market_id: str, data: Dict[str, Any], timestamp: float)
```

#### Key Properties

| Property | Type | Description |
|----------|------|-------------|
| `market_id` | `str` | Market identifier |
| `probability` | `float` | Current probability |
| `volume` | `float` | Total volume |
| `liquidity` | `float` | Current liquidity |
| `price` | `float` | Current price |
| `title` | `str` | Market title |
| `data_sources` | `list` | Which APIs provided the data |
| `is_fresh` | `bool` | Whether data is current |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `calculate_shift` | `(previous: MarketSnapshot) -> Dict[str, float]` | Calculate changes from a previous snapshot |

## Scoring / Algorithms

### Shift Detection

A shift is detected when any metric's change exceeds its threshold:

| Metric | Default Threshold | Calculation |
|--------|-------------------|-------------|
| Probability | 10.0 (percentage points) | `current.probability - previous.probability` |
| Volume | 50.0% | `((current - previous) / previous) * 100` |
| Liquidity | 30.0% | `((current - previous) / previous) * 100` |

Thresholds are passed as a dict parameter, allowing callers to customize sensitivity.

### Volatility Calculation

Standard deviation of probability changes over a rolling window:

```
changes = [snapshot[i].probability - snapshot[i-1].probability for i in window]
mean = sum(changes) / len(changes)
volatility = sqrt(sum((x - mean)^2 for x in changes) / len(changes))
```

Default window: 10 snapshots.

### Data Aggregation

For each market snapshot, the scanner fetches:
1. **Gamma API**: Market metadata (`get_market`), prices (`get_market_prices`)
2. **CLOB API**: Ticker data (`get_ticker`), order book (`get_order_book`)

These are merged into a unified dict with fields: `market_id`, `title`, `probability`, `price`, `volume`, `liquidity`, `last_trade_price`, `spread`.

### Concurrent Scanning

`scan_markets()` uses a `ThreadPoolExecutor` with 10 workers. Each market is scanned in parallel with a 10-second timeout per future.

### Data Freshness Validation

When scanning all active markets, the scanner:
1. Uses `APIAggregator.get_live_markets()` with optional volume filtering
2. Calls `aggregator.validate_data_freshness()` to detect stale data
3. Logs warnings for stale markets and data issues

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `check_interval` | 60 seconds | Pause between monitoring loop iterations |
| `max_snapshots_per_market` | 100 | Maximum stored snapshots per market |
| `require_fresh_data` | `True` | Require fresh data in all-market scans |
| `max_data_age_hours` | 24 | Maximum acceptable data age |
| Thread pool workers | 10 | Concurrent market scan threads |

## Data Sources

- **Gamma REST API** (`api/gamma.py`): Market metadata, prices, active market lists
- **CLOB REST API** (`api/clob.py`): Ticker data, order book, spread calculation
- **APIAggregator** (`api/aggregator.py`): Live markets with fallback and data validation

## Output Format

### Shift Detection Result

```python
{
    'market_id': str,
    'title': str,
    'timestamp': float,  # Unix timestamp
    'shift_type': ['probability', 'volume', 'liquidity'],  # Which thresholds were exceeded
    'changes': {
        'probability_change': float,
        'volume_change': float,      # percentage
        'liquidity_change': float,   # percentage
        'price_change': float,       # percentage
    },
    'current': dict,   # Current snapshot data
    'previous': dict,  # Previous snapshot data
}
```

## External Dependencies

- `polyterm.api.gamma.GammaClient`
- `polyterm.api.clob.CLOBClient`
- `polyterm.api.aggregator.APIAggregator`
- `polyterm.utils.json_output.safe_float`
- `concurrent.futures.ThreadPoolExecutor`

## Related

- CLI command: `polyterm monitor --limit 20`
- TUI screens: `1/m` (monitor), `2/l` (live monitor)
- Interacts with: `api/aggregator.py` (data fetching), `notifications.py` (shift alerts)
