# Analytics

> Market analytics engine for whale tracking, correlations, price predictions, and portfolio analysis.

## Overview

The analytics module provides an `AnalyticsEngine` that combines data from the Gamma API, CLOB API, and Data API to perform whale activity detection, market correlation analysis, price movement prediction, portfolio analytics, and market manipulation detection. It acts as a high-level analytics layer that sits on top of the API clients and aggregates multiple data signals.

## Key Classes and Functions

### `WhaleActivity`

Data class representing a single whale trade or volume-based activity detection.

#### Constructor

```python
WhaleActivity(trade_data: Dict[str, Any])
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `trader` | `str` | Wallet address when known. Empty for volume heuristics. Never `"Volume Spike"`. |
| `market_id` | `str` | Market identifier |
| `outcome` | `str` | Market direction: `"YES"`, `"NO"`, `"MIXED"`, or `"Unknown"` |
| `shares` | `float` | Estimated share count |
| `price` | `float` | Last trade price |
| `notional` | `float` | Dollar value of the activity |
| `timestamp` | `int` | Unix timestamp |
| `tx_hash` | `str` | Transaction hash (empty for volume-based detection) |
| `data` | `Dict` | Original raw trade data |

### `MarketCorrelation`

Data class representing correlation between two markets.

#### Constructor

```python
MarketCorrelation(market1_id: str, market2_id: str, correlation: float)
```

### `AnalyticsEngine`

Main analytics class that coordinates data from multiple API sources.

#### Constructor

```python
AnalyticsEngine(
    gamma_client: GammaClient,
    clob_client: CLOBClient,
    data_api_client: Optional[DataAPIClient] = None,
)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `track_whale_trades` | `(min_notional: float = 10000, lookback_hours: int = 24) -> List[WhaleActivity]` | Compatibility wrapper over `volume_spikes.detect_high_volume_markets`. Does not identify traders. Prefer `--wallets` for whale identity. |
| `get_whale_impact_on_market` | `(market_id: str, whale_address: str) -> Dict[str, Any]` | Analyze a specific whale's impact on a market |
| `identify_whale_followers` | `(whale_address: str) -> List[Dict[str, Any]]` | Raises `FeatureUnavailable`. Not implemented. |
| `calculate_market_correlation` | `(market1_id: str, market2_id: str, window_hours: int = 24) -> Optional[MarketCorrelation]` | Raises `FeatureUnavailable`. Use `CorrelationEngine` for real correlations. |
| `find_correlated_markets` | `(market_id: str, min_correlation: float = 0.7, limit: int = 5) -> List[MarketCorrelation]` | Raises `FeatureUnavailable`. Use `CorrelationEngine.find_correlated_markets`. |
| `analyze_historical_trends` | `(market_id: str, hours: int = 168) -> Dict[str, Any]` | Raises `FeatureUnavailable`. No time-series source is wired. |
| `predict_price_movement` | `(market_id: str, horizon_hours: int = 24) -> Dict[str, Any]` | Raises `FeatureUnavailable`. Would invent a signal from missing trends. |
| `get_portfolio_analytics` | `(wallet_address: str) -> Dict[str, Any]` | Calculate portfolio value, P&L, and ROI from Data API positions |
| `detect_market_manipulation` | `(market_id: str) -> Dict[str, Any]` | Raises `FeatureUnavailable`. No on-chain source is wired. |

## Scoring / Algorithms

### Whale Detection

Volume-based **market** heuristic using 24-hour Gamma volume. This is not whale identity:

1. Delegate to `volume_spikes.detect_high_volume_markets`
2. Markets with `volume24hr >= min_notional` (default $10,000) are flagged
3. `trader` is left empty; `evidence_level` is `gamma_volume24hr_heuristic`
4. Outcome lean inferred from YES price thresholds (`> 0.65` YES, `< 0.35` NO, else MIXED)
5. Results sorted by 24h volume descending

For attributable whale prints use `polyterm whales --wallets` (`scan_whale_prints`). Agent `wallet.whales` still uses `WalletIntelligence.live_whales`.

### Price Movement Prediction

`predict_price_movement` raises `FeatureUnavailable`. It used to treat missing
historical trends as zero momentum and emit a `stable` prediction, which is
not a real signal. Use `PredictionEngine` (local snapshots) when you have data.

### Portfolio Analytics

Aggregates position data from the Data API:
- Iterates all positions, extracting `size`, `averagePrice`, `currentValue`, `initialValue`, `realizedPnL`, `unrealizedPnL`
- Handles multiple field name variants for API compatibility
- ROI: `(total_pnl / total_invested) * 100`

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_notional` | `10000` | Minimum 24h volume for whale detection ($) |
| `lookback_hours` | `24` | Time window for whale tracking |
| `min_correlation` | `0.7` | Minimum correlation threshold |
| `horizon_hours` | `24` | Prediction time horizon |

## Data Sources

- **Gamma API** (`api/gamma.py`): Market listings, volume, prices
- **CLOB API** (`api/clob.py`): Order book and trade data
- **Data API** (`api/data_api.py`): Wallet positions, trade history, P&L

## Output Format

### `track_whale_trades` returns

```python
List[WhaleActivity]  # sorted by notional, descending
```

### Unimplemented analytics

These methods raise `polyterm.utils.errors.FeatureUnavailable` instead of
returning `[]`, `None`, or `{}`:

- `identify_whale_followers`
- `calculate_market_correlation`
- `find_correlated_markets`
- `analyze_historical_trends`
- `predict_price_movement`
- `detect_market_manipulation`

Empty collections are reserved for real "no results" from live sources
(`track_whale_trades`, `get_portfolio_analytics`).

### `get_portfolio_analytics` returns

```python
{
    "wallet_address": str,
    "total_positions": int,
    "total_value": float,
    "total_pnl": float,
    "total_invested": float,
    "roi_percent": float,
    "positions": List[Dict],
    "data_source": "data_api",
    "source": "data_api",
    "lag": True,
    "lagged": True,
}
```

## External Dependencies

- `polyterm.api.gamma.GammaClient`
- `polyterm.api.clob.CLOBClient`
- `polyterm.api.data_api.DataAPIClient`
- `polyterm.utils.json_output.safe_float`

## Related

- CLI commands: `polyterm whales` (volume heuristic via `volume_spikes`; `--wallets` for identity), `polyterm predict`, `polyterm dashboard`
- TUI screens: `3/w` (whales), `5/a` (analytics), `10/pred` (predictions)
- Other modules: `core/whale_tracker.py` (more advanced whale tracking with insider detection), `core/predictions.py` (multi-factor prediction engine), `core/correlation.py` (dedicated correlation engine)
