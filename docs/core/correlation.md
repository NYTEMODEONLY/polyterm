# Correlation

> Market correlation analysis engine with rolling correlations, cluster detection, break alerts, and ASCII heatmaps.

## Overview

The correlation module calculates statistical relationships between prediction markets using Pearson correlation on price time series data. It supports pairwise correlation, full correlation matrices, market clustering via connected components, correlation break detection (short-term vs long-term divergence), and ASCII heatmap rendering. All price data is sourced from the local SQLite database's market snapshots.

## Key Classes and Functions

### `CorrelationResult`

Dataclass representing the correlation between two markets.

```python
@dataclass
class CorrelationResult:
    market1_id: str
    market2_id: str
    market1_title: str
    market2_title: str
    correlation: float          # -1 to 1
    sample_size: int
    time_window_hours: int
    calculated_at: datetime     # auto-set to now
```

#### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `strength` | `str` | Human-readable strength label |
| `direction` | `str` | `"positive"`, `"negative"`, or `"neutral"` |

#### Correlation Strength Thresholds

| Absolute Correlation | Strength Label |
|---------------------|----------------|
| >= 0.8 | `"very_strong"` |
| >= 0.6 | `"strong"` |
| >= 0.4 | `"moderate"` |
| >= 0.2 | `"weak"` |
| < 0.2 | `"negligible"` |

#### Direction Thresholds

| Correlation | Direction |
|-------------|-----------|
| > 0.1 | `"positive"` |
| < -0.1 | `"negative"` |
| -0.1 to 0.1 | `"neutral"` |

### `MarketCluster`

Dataclass representing a group of correlated markets.

```python
@dataclass
class MarketCluster:
    cluster_id: int
    markets: List[str]          # Market IDs
    market_titles: List[str]
    avg_correlation: float
    category: Optional[str] = None
```

### `CorrelationEngine`

Main engine for all correlation calculations.

#### Constructor

```python
CorrelationEngine(
    database: Database,
    gamma_client: Optional[GammaClient] = None,
)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `calculate_correlation` | `(market1_id: str, market2_id: str, hours: int = 24) -> Optional[CorrelationResult]` | Calculate Pearson correlation between two markets |
| `find_correlated_markets` | `(market_id: str, min_correlation: float = 0.5, max_results: int = 10, hours: int = 24) -> List[CorrelationResult]` | Find markets correlated with a given market |
| `calculate_correlation_matrix` | `(market_ids: List[str], hours: int = 24) -> Dict[str, Dict[str, float]]` | Calculate full pairwise correlation matrix |
| `find_market_clusters` | `(market_ids: List[str], min_correlation: float = 0.6, hours: int = 24) -> List[MarketCluster]` | Group markets into clusters using connected components |
| `detect_correlation_breaks` | `(market1_id: str, market2_id: str, short_window: int = 6, long_window: int = 72, threshold: float = 0.3) -> Optional[Dict]` | Detect when short-term correlation diverges from long-term |
| `render_heatmap_ascii` | `(market_ids: List[str], hours: int = 24, width: int = 60) -> str` | Render correlation matrix as ASCII art heatmap |

#### Private Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `_get_price_series` | `(market_id: str, hours: int) -> List[Tuple[datetime, float]]` | Fetch price series from database snapshots |
| `_align_series` | `(series1, series2, tolerance_minutes: int = 15) -> List[Tuple[datetime, float, float]]` | Align two time series by matching closest timestamps |
| `_pearson_correlation` | `(x: List[float], y: List[float]) -> float` | Calculate Pearson correlation coefficient |
| `_get_market_title` | `(market_id: str) -> str` | Look up market title |

## Scoring / Algorithms

### Pearson Correlation Coefficient

Implemented from scratch (no NumPy dependency):

```
cov = sum((x[i] - mean_x) * (y[i] - mean_y)) / n
std_x = sqrt(sum((xi - mean_x)^2) / n)
std_y = sqrt(sum((yi - mean_y)^2) / n)
correlation = cov / (std_x * std_y)
```

Returns 0.0 if either standard deviation is zero.

### Time Series Alignment

Two price series are aligned by matching timestamps within a `tolerance_minutes` window (default 15 minutes). For each point in series1, the closest timestamp in series2 is found. A minimum of 5 aligned data points is required for correlation calculation.

### Market Clustering

Uses a BFS-based connected components algorithm:

1. Build adjacency graph: edge between markets if `abs(correlation) >= min_correlation`
2. BFS traversal to find connected components
3. Average intra-cluster correlation calculated for each cluster

### Correlation Break Detection

Compares short-term (default 6h) vs long-term (default 72h) correlation:

```
diff = short_term_correlation - long_term_correlation
if abs(diff) >= threshold (default 0.3):
    alert triggered
```

Direction: `"strengthening"` if diff > 0, `"weakening"` if diff < 0.

### ASCII Heatmap Symbols

| Symbol | Correlation Range |
|--------|-------------------|
| `+++` | >= 0.8 |
| `++` | >= 0.5 |
| `+` | >= 0.2 |
| `.` | -0.2 to 0.2 |
| `-` | <= -0.2 |
| `--` | <= -0.5 |
| `---` | <= -0.8 |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `hours` | `24` | Default time window for correlation |
| `min_correlation` | `0.5` (find), `0.6` (cluster) | Minimum absolute correlation |
| `max_results` | `10` | Maximum correlated markets returned |
| `tolerance_minutes` | `15` | Timestamp alignment tolerance |
| `short_window` | `6` hours | Short-term window for break detection |
| `long_window` | `72` hours | Long-term window for break detection |
| `threshold` | `0.3` | Minimum difference for break alert |
| `_cache_ttl` | `300` seconds (5 min) | Price cache TTL |

## Data Sources

- **Database** (`db/database.py`): `MarketSnapshot` records from `market_snapshots` table
  - `get_market_history(market_id, hours)` for price series
  - Direct SQL query on `market_snapshots` for unique market ID discovery
- **Gamma API** (`api/gamma.py`): Market title lookup (optional)

## Output Format

### `calculate_correlation` returns

`CorrelationResult` dataclass with `.to_dict()` serialization:

```python
{
    "market1_id": "abc123",
    "market2_id": "def456",
    "market1_title": "...",
    "market2_title": "...",
    "correlation": 0.85,
    "strength": "very_strong",
    "direction": "positive",
    "sample_size": 48,
    "time_window_hours": 24,
    "calculated_at": "2026-04-03T12:00:00",
}
```

### `detect_correlation_breaks` returns

```python
{
    "market1_id": "abc123",
    "market2_id": "def456",
    "short_term_correlation": 0.3,
    "long_term_correlation": 0.8,
    "difference": -0.5,
    "direction": "weakening",
    "alert": True,
    "message": "Correlation weakened by 0.50",
}
```

### ASCII heatmap example

```
Correlation Heatmap
============================================================

            abc   def   ghi
abc          +++ ++   .
def          ++  +++  -
ghi           .   -  +++

Legend: +++ (>0.8) ++ (>0.5) + (>0.2) . (neutral) - (<-0.2) -- (<-0.5) --- (<-0.8)
```

## External Dependencies

- `math` (standard library) -- for `sqrt`
- `polyterm.db.database.Database`
- `polyterm.db.models.MarketSnapshot`
- `polyterm.api.gamma.GammaClient` (optional)

## Related

- CLI commands: `polyterm correlate`
- TUI screens: `corr` shortcut
- Other modules: `core/analytics.py` (has its own `MarketCorrelation` class, delegates to this module for deeper analysis), `core/arbitrage.py` (correlated market arbitrage uses title similarity rather than price correlation)
