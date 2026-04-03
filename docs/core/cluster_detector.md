# Cluster Detector

> Wallet cluster detection for identifying wallets likely controlled by the same entity.

## Overview

The cluster detector module identifies groups of blockchain wallets that appear to be operated by the same person or entity. It combines three independent detection signals -- timing correlation, market overlap, and trade size patterns -- into a single 0-100 confidence score. This helps detect potential market manipulation through coordinated multi-wallet trading.

## Key Classes and Functions

### `WalletClusterDetector`

Main detection class that analyzes wallet behavior patterns from trade history stored in the local database.

#### Constructor

```python
WalletClusterDetector(database)
```

The `database` parameter is a `Database` instance from `db/database.py`.

#### Class Attributes

| Attribute | Value | Description |
|-----------|-------|-------------|
| `SIGNALS` | `['timing_correlation', 'market_overlap', 'size_pattern']` | List of detection signal names |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `find_timing_clusters` | `(window_seconds=30) -> List[Tuple[str, str, int]]` | Find wallet pairs that trade within seconds of each other |
| `find_market_overlap_clusters` | `(min_overlap=0.7) -> List[Tuple[str, str, float]]` | Find wallets with high Jaccard similarity in traded markets |
| `find_size_pattern_clusters` | `() -> List[Tuple[str, str, int]]` | Find wallets using identical trade sizes |
| `calculate_cluster_score` | `(wallet1, wallet2, timing_lookup=None) -> Dict[str, Any]` | Calculate 0-100 combined confidence score for a wallet pair |
| `detect_clusters` | `(min_score=60) -> List[Dict]` | Run all detection methods and return scored clusters |

#### Private Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `_build_timing_lookup` | `(timing_clusters: List[Tuple[str, str, int]]) -> Dict[Tuple[str, str], int]` | Build O(1) lookup map from timing results |

## Scoring / Algorithms

### Signal 1: Timing Correlation (up to 40 points)

- Looks back 168 hours (1 week) of trades, up to 5,000 records
- Trades sorted newest-first for early termination
- Two wallets trading within `window_seconds` (default 30) are flagged
- Minimum 3 co-occurring trades required to qualify
- Score: `min(correlation_count * 10, 40)`

### Signal 2: Market Overlap (up to 35 points)

- Builds set of traded markets for each wallet (minimum 2 markets per wallet)
- Calculates Jaccard similarity: `|intersection| / |union|`
- Minimum overlap of `min_overlap` (default 0.7) to qualify
- Score: `int(overlap * 35)`

### Signal 3: Size Pattern (up to 25 points)

- Collects unique trade sizes per wallet (rounded to 2 decimal places)
- Counts common sizes between wallet pairs
- Minimum 3 matching sizes required in `find_size_pattern_clusters`
- Minimum 2 matching sizes required for scoring
- Score: `min(common_sizes * 5, 25)`

### Combined Score

```
total_score = timing_score + overlap_score + size_score
final_score = min(total_score, 100)
```

### Risk Levels

| Score Range | Risk Level |
|-------------|------------|
| 70-100 | `"high"` |
| 40-69 | `"medium"` |
| 0-39 | `"low"` |

### Cluster Detection Pipeline

1. Run all three signal detectors independently
2. Collect unique wallet pairs from all detectors
3. Score each pair using `calculate_cluster_score`
4. Filter pairs with score >= `min_score` (default 60)
5. Return clusters sorted by score descending

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `window_seconds` | `30` | Maximum time gap for timing correlation |
| `min_overlap` | `0.7` | Minimum Jaccard similarity for market overlap |
| `min_score` | `60` | Minimum combined score to report a cluster |
| Trade lookback | `168` hours (1 week) | Time window for timing analysis |
| Trade limit | `5000` | Maximum trades for timing analysis |
| Wallet limit | `200` | Maximum wallets to analyze |
| Trade limit per wallet | `500` (overlap), `200` (size) | Per-wallet trade fetch limits |

## Data Sources

- **Database** (`db/database.py`): All trade history, wallet lists
  - `get_recent_trades(hours, limit)` -- for timing correlation
  - `get_all_wallets(limit)` -- for overlap and size analysis
  - `get_trades_by_wallet(address, limit)` -- for per-wallet trade details

## Output Format

### `detect_clusters` returns

```python
[
    {
        "wallets": ["0xabc...", "0xdef..."],
        "score": 85,
        "risk": "high",
        "signals": ["timing:5", "overlap:72.3%", "sizes:4"],
        "detected_at": "2026-04-03T12:00:00",
    },
    ...
]
```

### `calculate_cluster_score` returns

```python
{
    "score": 75,          # 0-100
    "signals": ["timing:5", "overlap:72.3%", "sizes:4"],
    "risk": "high",       # high, medium, low
}
```

## External Dependencies

None beyond the project's own `db/database.py`.

## Related

- CLI commands: `polyterm clusters --min-score 70`
- TUI screens: `cl` shortcut
- Other modules: `core/whale_tracker.py` (insider detection scores individual wallets), `core/wash_trade_detector.py` (volume manipulation detection)
