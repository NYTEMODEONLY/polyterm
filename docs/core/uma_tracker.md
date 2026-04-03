# UMA Tracker

> UMA oracle dispute risk analysis for Polymarket resolution.

## Overview

The UMA tracker module analyzes markets for resolution dispute risk by evaluating five factors: subjective language, category history, resolution source reliability, time to resolution, and description clarity. Polymarket uses the UMA Optimistic Oracle for market resolution, and this module helps traders assess how likely a market is to face a dispute during the resolution process.

## Key Classes and Functions

### `UMADisputeTracker`

Analyzes markets for dispute risk and tracks active disputes.

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `analyze_resolution_risk` | `(market_id: str, title: str, description: str, category: str = "", resolution_source: str = "", end_date: Optional[datetime] = None) -> ResolutionAnalysis` | Comprehensive dispute risk analysis |
| `get_risk_color` | `(risk_level: ResolutionRisk) -> str` | Get Rich color for risk level display |
| `get_risk_description` | `(risk_level: ResolutionRisk) -> str` | Get human-readable risk description |

### `ResolutionAnalysis`

Dataclass containing the complete resolution risk assessment.

| Field | Type | Description |
|-------|------|-------------|
| `market_id` | `str` | Market identifier |
| `market_title` | `str` | Market question/title |
| `risk_level` | `ResolutionRisk` | Categorical risk level |
| `risk_score` | `int` | Numeric score 0-100 |
| `factors` | `Dict[str, dict]` | Per-factor breakdown with score, weight, details |
| `warnings` | `List[str]` | Warning messages |
| `recommendations` | `List[str]` | Actionable recommendations |

### `UMADispute`

Dataclass representing an individual UMA oracle dispute.

| Field | Type | Description |
|-------|------|-------------|
| `market_id` | `str` | Market identifier |
| `market_title` | `str` | Market title |
| `proposed_answer` | `str` | Originally proposed resolution |
| `dispute_reason` | `Optional[str]` | Reason for dispute |
| `status` | `DisputeStatus` | Current dispute status |
| `proposed_at` | `datetime` | When answer was proposed |
| `dispute_deadline` | `Optional[datetime]` | Deadline to file dispute |
| `bond_amount` | `float` | Bond required for dispute |

### `DisputeStatus` (Enum)

`NONE`, `PENDING`, `DISPUTED`, `RESOLVED_ORIGINAL`, `RESOLVED_DISPUTED`, `TIMEOUT`.

### `ResolutionRisk` (Enum)

`LOW`, `MEDIUM`, `HIGH`, `VERY_HIGH`.

## Scoring / Algorithms

### Factor Weights

| Factor | Weight | Description |
|--------|--------|-------------|
| Subjectivity | 30% | Subjective language in title/description |
| Resolution Source | 25% | Reliability of resolution data source |
| Category | 20% | Historical dispute rate by category |
| Time Risk | 15% | Time until resolution |
| Description Clarity | 10% | Quality and specificity of description |

### Risk Levels

| Risk Level | Score Range | Description |
|------------|-------------|-------------|
| Low | 0-25 | Clear resolution criteria, low dispute risk |
| Medium | 26-45 | Some subjectivity, moderate dispute risk |
| High | 46-65 | Significant dispute risk, trade with caution |
| Very High | 66-100 | High dispute risk, careful position sizing recommended |

### Subjectivity Scoring (0-100)

Scans title and description for subjective keywords:

| Keywords Found | Score |
|----------------|-------|
| 0 | 15 |
| 1 | 40 |
| 2-3 | 65 |
| 4+ | 85 |

Subjective keywords: `best`, `most`, `significant`, `major`, `meaningful`, `substantial`, `successful`, `effective`, `important`, `controversial`, `unprecedented`, `historic`, `notable`.

### Category Risk Scoring (0-100)

| Category Type | Score | Examples |
|---------------|-------|----------|
| High-risk | 70 | politics, government, regulation, legal, controversial, opinion, social |
| Objective | 25 | crypto, sports, finance |
| Other known | 40 | Any other specified category |
| Unknown | 50 | No category provided |

### Resolution Source Scoring (0-100)

| Source Type | Score |
|-------------|-------|
| Reliable source found | 20 |
| References "official" | 30 |
| Other specified source | 50 |
| No source specified | 75 |

Reliable sources: `associated press`, `ap news`, `reuters`, `official government`, `official results`, `blockchain`, `oracle`, `on-chain`, `official statistics`, `official announcement`.

### Time Risk Scoring (0-100)

| Days Until Resolution | Score |
|-----------------------|-------|
| Ended | 30 |
| <= 7 days | 20 |
| <= 30 days | 35 |
| <= 90 days | 50 |
| <= 365 days | 70 |
| > 365 days | 85 |
| No end date | 50 |

### Description Clarity Scoring (0-100)

| Condition | Score |
|-----------|-------|
| No description | 80 |
| < 50 characters | 70 |
| < 150 chars, no criteria | 55 |
| Has clarity indicators | 20 |
| Adequate length | 40 |

Clarity indicators: `will resolve`, `resolves to`, `resolution criteria`, `determined by`, `based on`, `according to`.

## Configuration

All scoring thresholds, keywords, and category lists are defined as class constants on `UMADisputeTracker`. The tracker also maintains `active_disputes` and `historical_disputes` lists (populated externally -- in production these would come from the UMA API).

## Data Sources

- All inputs are passed as parameters to `analyze_resolution_risk()` -- no direct API calls
- In production, dispute data would come from the UMA Optimistic Oracle API
- Currently uses simulated dispute lists

## Output Format

`ResolutionAnalysis.to_dict()` returns:

```python
{
    'market_id': str,
    'market_title': str,
    'risk_level': 'low' | 'medium' | 'high' | 'very_high',
    'risk_score': int,  # 0-100
    'factors': {
        'subjectivity': {'score': int, 'weight': float, 'details': str},
        'category': {'score': int, 'weight': float, 'details': str},
        'resolution_source': {'score': int, 'weight': float, 'details': str},
        'time_risk': {'score': int, 'weight': float, 'details': str},
        'description_clarity': {'score': int, 'weight': float, 'details': str},
    },
    'warnings': [str],
    'recommendations': [str],
}
```

## External Dependencies

- None (stdlib only: `dataclasses`, `datetime`, `enum`)

## Related

- CLI command: `polyterm risk --market "bitcoin"` (risk assessment includes UMA analysis)
- TUI screen: `14/risk` (risk assessment)
- Interacts with: `risk_score.py` (resolution clarity factor overlaps), market data from `api/gamma.py`
