# Risk Score

> Market risk scoring system with letter grades (A-F) across six weighted factors.

## Overview

The risk score module evaluates Polymarket markets on multiple risk dimensions to help traders identify and avoid problematic bets. It produces a composite 0-100 risk score that maps to letter grades A through F, along with per-factor breakdowns, warnings, and actionable recommendations.

## Key Classes and Functions

### `MarketRiskScorer`

Scores markets across six risk factors with configurable weights.

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `score_market` | `(market_id: str, title: str, description: str = "", end_date: Optional[datetime] = None, volume_24h: float = 0, liquidity: float = 0, spread: float = 0, category: str = "", resolution_source: str = "") -> RiskAssessment` | Score a market's overall risk level |
| `get_grade_description` | `(grade: str) -> str` | Get human-readable grade description |
| `get_grade_color` | `(grade: str) -> str` | Get Rich color for grade display |

### `RiskAssessment`

Dataclass containing the complete risk assessment result.

| Field | Type | Description |
|-------|------|-------------|
| `market_id` | `str` | Market identifier |
| `market_title` | `str` | Market question/title |
| `overall_grade` | `str` | Letter grade A-F |
| `overall_score` | `int` | Numeric score 0-100 (higher = riskier) |
| `factors` | `Dict[str, Dict]` | Per-factor breakdown with score, weight, reason |
| `warnings` | `List[str]` | Warning messages for high-risk factors |
| `recommendations` | `List[str]` | Actionable trading recommendations |

## Scoring / Algorithms

### Factor Weights

| Factor | Weight | Description |
|--------|--------|-------------|
| Resolution Clarity | 25% | How objective/clear the resolution criteria are |
| Liquidity | 20% | Depth and quality of market liquidity |
| Time Risk | 15% | Duration until market resolution |
| Volume Quality | 15% | Volume patterns and wash trade indicators |
| Spread | 15% | Bid-ask spread width |
| Category Risk | 10% | Historical dispute rate by market category |

### Grade Scale

| Grade | Score Range | Description |
|-------|-------------|-------------|
| A | 0-20 | Low Risk -- clear resolution, good liquidity |
| B | 21-35 | Moderate-Low Risk -- generally safe with minor concerns |
| C | 36-50 | Moderate Risk -- some concerns, trade with caution |
| D | 51-70 | High Risk -- multiple concerns, proceed carefully |
| F | 71-100 | Very High Risk -- consider avoiding this market |

### Resolution Clarity Scoring (0-100)

- Subjective keywords detected (3+): +40 points
- Subjective keywords detected (1-2): +20 points
- No clear resolution source: +25 points
- Question format needs interpretation (no "will"/"does"): +15 points
- Has specific numeric criteria (dates, percentages, dollar amounts): -10 points
- Subjective keywords checked: `effectively`, `essentially`, `significant`, `major`, `meaningful`, `substantial`, `largely`, `mainly`, `generally`, `typically`, `consensus`, `widely`, `broadly`, `most people`, `mainstream`

### Liquidity Scoring (0-100)

| Liquidity | Score | Label |
|-----------|-------|-------|
| >= $500,000 | 0 | Excellent |
| >= $100,000 | 15 | Good |
| >= $50,000 | 30 | Moderate |
| >= $10,000 | 50 | Low |
| >= $1,000 | 70 | Very low |
| < $1,000 | 90 | Minimal |
| No data | 80 | Unknown |

### Time Risk Scoring (0-100)

| Days Remaining | Score |
|----------------|-------|
| Ended | 0 |
| <= 1 day | 10 |
| <= 7 days | 15 |
| <= 30 days | 25 |
| <= 90 days | 40 |
| <= 365 days | 60 |
| > 365 days | 80 |
| No end date | 50 |

### Volume Quality Scoring (0-100)

Based on 24h volume-to-liquidity ratio:

| Ratio | Score | Interpretation |
|-------|-------|----------------|
| > 5.0x | 85 | Possible wash trading |
| > 2.0x | 60 | Elevated |
| > 0.5x | 20 | Healthy |
| > 0.1x | 30 | Low activity |
| <= 0.1x | 45 | Very low activity |
| No volume | 40 | No recent volume |

### Spread Scoring (0-100)

| Spread | Score | Label |
|--------|-------|-------|
| <= 1% | 0 | Very tight |
| <= 2% | 15 | Good |
| <= 5% | 35 | Moderate |
| <= 10% | 55 | Wide |
| > 10% | 80 | Very wide |
| No data | 50 | Unknown |

### Category Risk Scoring (0-100)

- **High-risk categories** (score 60): politics, legal, regulatory, media, social
- **Low-risk categories** (score 15): sports, crypto, finance, weather, science
- **Other/unknown** (score 35): Average risk

### Warning and Recommendation Triggers

| Condition | Warning/Recommendation |
|-----------|----------------------|
| Resolution clarity >= 60 | "Resolution criteria may be subjective or unclear" |
| Liquidity >= 60 | "Low liquidity - large orders may cause slippage" |
| Time risk >= 60 | "Long time to resolution - capital locked up" |
| Volume quality >= 70 | "Volume pattern may indicate wash trading" |
| Spread >= 50 | "Use limit orders to avoid paying the spread" |
| Category >= 60 | "Category has higher historical dispute rate" |
| Grade D or F | "Consider finding a lower-risk alternative" |

## Configuration

All scoring thresholds and weights are defined as class constants on `MarketRiskScorer`. The `WEIGHTS` dict must sum to 1.0.

## Data Sources

- All inputs are passed as parameters to `score_market()` -- no direct API or database calls
- Designed to be called with data from `GammaClient` or `APIAggregator`

## Output Format

`RiskAssessment.to_dict()` returns:

```python
{
    'market_id': str,
    'market_title': str,
    'overall_grade': 'A' | 'B' | 'C' | 'D' | 'F',
    'overall_score': int,  # 0-100
    'factors': {
        'resolution_clarity': {'score': int, 'weight': float, 'reason': str},
        'liquidity': {'score': int, 'weight': float, 'reason': str},
        'time_risk': {'score': int, 'weight': float, 'reason': str},
        'volume_quality': {'score': int, 'weight': float, 'reason': str},
        'spread': {'score': int, 'weight': float, 'reason': str},
        'category_risk': {'score': int, 'weight': float, 'reason': str},
    },
    'warnings': [str],
    'recommendations': [str],
}
```

## External Dependencies

- None (stdlib only: `dataclasses`, `re`, `datetime`)

## Related

- CLI command: `polyterm risk --market "bitcoin"`
- TUI screen: `14/risk` (risk assessment)
- Interacts with: `wash_trade_detector.py` (volume quality overlaps), `uma_tracker.py` (resolution risk overlaps)
