# Wash Trade Detector

> Detect potential wash trading and artificial volume in Polymarket markets.

## Overview

The wash trade detector identifies suspicious trading patterns that may indicate artificial volume inflation. Based on research suggesting approximately 25% of Polymarket volume may be wash trading, this module evaluates five indicators: volume/liquidity ratio, trader concentration, trade size uniformity, YES/NO side balance, and volume anomalies. It provides both a detailed market analysis and a quick-score utility function for integration into other modules.

## Key Classes and Functions

### `WashTradeDetector`

Analyzes markets for wash trading indicators across five dimensions.

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `analyze_market` | `(market_id: str, title: str, volume_24h: float = 0, liquidity: float = 0, trade_count_24h: int = 0, unique_traders_24h: int = 0, avg_trade_size: float = 0, median_trade_size: float = 0, yes_volume: float = 0, no_volume: float = 0) -> WashTradeAnalysis` | Full wash trade analysis for a market |
| `get_risk_color` | `(risk_level: WashTradeRisk) -> str` | Get Rich color for risk level display |
| `get_risk_description` | `(risk_level: WashTradeRisk) -> str` | Get human-readable risk description |

### `quick_wash_trade_score(volume_24h, liquidity)`

Standalone utility function for quick wash trade scoring from other modules.

```python
def quick_wash_trade_score(volume_24h: float, liquidity: float) -> Tuple[int, str]
```

Returns a `(score, description)` tuple based solely on volume/liquidity ratio.

### `WashTradeAnalysis`

Dataclass containing the complete analysis result.

| Field | Type | Description |
|-------|------|-------------|
| `market_id` | `str` | Market identifier |
| `market_title` | `str` | Market title |
| `risk_level` | `WashTradeRisk` | Categorical risk level |
| `overall_score` | `int` | Composite score 0-100 (higher = more suspicious) |
| `indicators` | `List[WashTradeIndicator]` | Individual indicator results |
| `recommendations` | `List[str]` | Actionable recommendations |

### `WashTradeIndicator`

Dataclass representing a single wash trade indicator.

| Field | Type | Description |
|-------|------|-------------|
| `indicator_type` | `str` | Indicator category |
| `score` | `int` | Individual score 0-100 |
| `description` | `str` | Summary description |
| `details` | `Optional[str]` | Detailed explanation |

### `WashTradeRisk` (Enum)

`LOW`, `MEDIUM`, `HIGH`, `VERY_HIGH`.

## Scoring / Algorithms

### Risk Levels

| Risk Level | Score Range | Description |
|------------|-------------|-------------|
| Low | 0-25 | Trading patterns appear organic |
| Medium | 26-45 | Some unusual patterns detected |
| High | 46-65 | Multiple wash trading indicators present |
| Very High | 66-100 | Strong evidence of artificial volume |

### Overall Score Calculation

Indicators are combined using a self-weighting average where higher-scoring indicators receive more weight:

```
weight_i = 1.0 + (score_i / 100)
overall = sum(score_i * weight_i) / sum(weight_i)
```

When no indicator data is available, the default score is 40 (uncertain).

### Indicator 1: Volume/Liquidity Ratio

Compares 24-hour trading volume to current liquidity.

| Ratio | Score | Interpretation |
|-------|-------|----------------|
| > 10.0x | 90 | Extremely high -- strong wash trade signal |
| > 5.0x | 75 | Very high -- suspicious pattern |
| > 3.0x | 55 | Elevated |
| > 1.0x | 30 | Volume above liquidity |
| No liquidity data | 50 | Cannot assess |

### Indicator 2: Trader Concentration

Measures average trades per unique wallet.

| Trades per Trader | Score | Interpretation |
|-------------------|-------|----------------|
| > 20 | 85 | Extremely concentrated -- few wallets driving volume |
| > 10 | 65 | Highly concentrated |
| > 5 | 40 | Moderate concentration |
| <= 5 | -- | Not flagged |

### Indicator 3: Trade Size Uniformity

Compares median trade size to average trade size. In organic markets, average is typically much larger than median due to whale trades. Wash traders tend to use uniform sizes.

| Median/Avg Ratio | Score | Interpretation |
|------------------|-------|----------------|
| > 0.9 | 75 | Suspiciously uniform sizes |
| > 0.8 | 50 | Quite uniform |
| <= 0.8 | -- | Not flagged |

### Indicator 4: Side Balance

Checks if YES and NO volume are suspiciously balanced. Wash traders often trade both sides equally to inflate volume.

| Balance Ratio (min/max) | Score | Interpretation |
|-------------------------|-------|----------------|
| > 0.95 | 70 | Nearly perfectly balanced -- unusual symmetry |
| > 0.85 | 45 | Highly balanced |
| <= 0.85 | -- | Not flagged |

### Indicator 5: Volume Anomaly

Cross-checks reported volume against calculated volume (`trade_count * avg_trade_size`).

| Discrepancy | Score | Interpretation |
|-------------|-------|----------------|
| > 50% | 60 | Volume calculation discrepancy |
| <= 50% | -- | Not flagged |

### Quick Score Function

The `quick_wash_trade_score()` function provides a fast volume/liquidity check:

| Ratio | Score | Description |
|-------|-------|-------------|
| > 10.0x | 90 | Extreme volume anomaly |
| > 5.0x | 75 | Very high volume/liquidity |
| > 3.0x | 55 | Elevated volume/liquidity |
| > 1.5x | 35 | Volume above liquidity |
| > 0.5x | 20 | Normal trading pattern |
| <= 0.5x | 25 | Low trading activity |
| No liquidity | 50 | Cannot assess |
| No volume | 20 | No volume |

## Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `VOLUME_LIQUIDITY_THRESHOLD` | 3.0 | Volume/liquidity ratio for elevated flag |
| `TRADE_SIZE_UNIFORMITY_THRESHOLD` | 0.8 | Median/avg ratio for uniformity flag |
| `TIME_CLUSTERING_THRESHOLD` | 0.7 | Reserved for time clustering analysis |

## Data Sources

- All inputs are passed as parameters to `analyze_market()` -- no direct API calls
- Designed to receive data from `GammaClient` (volume, liquidity) and trade aggregation
- `quick_wash_trade_score()` is used by `risk_score.py` and the monitor command

## Output Format

`WashTradeAnalysis.to_dict()` returns:

```python
{
    'market_id': str,
    'market_title': str,
    'risk_level': 'low' | 'medium' | 'high' | 'very_high',
    'overall_score': int,  # 0-100
    'indicators': [
        {
            'type': str,  # e.g., 'volume_liquidity', 'trader_concentration'
            'score': int,
            'description': str,
            'details': str | None,
        }
    ],
    'recommendations': [str],
}
```

## External Dependencies

- None (stdlib only: `dataclasses`, `datetime`, `enum`)

## Related

- CLI command: `polyterm monitor --show-quality` (integrates wash trade scores)
- TUI screen: `1/m` (monitor with quality indicators)
- Interacts with: `risk_score.py` (volume quality factor), `scanner.py` (market monitoring)
