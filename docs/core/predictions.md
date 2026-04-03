# Predictions

> Signal-based multi-factor prediction engine for Polymarket markets.

## Overview

The predictions module generates directional forecasts for prediction markets by combining multiple independent signals into a weighted composite score. It supports both database-sourced historical data and live API data as inputs, with an accuracy tracking system that records outcomes for calibration over time.

## Key Classes and Functions

### `PredictionEngine`

The core engine that generates predictions by computing individual signals and combining them via weighted averaging.

#### Constructor

```python
PredictionEngine(database: Database)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `generate_prediction` | `(market_id: str, market_title: str = "", horizon_hours: int = 24, market_data: Optional[Dict] = None) -> Prediction` | Generate a multi-signal prediction for a market |
| `record_outcome` | `(prediction: Prediction, actual_change: float) -> None` | Record prediction outcome for accuracy tracking |
| `verify_with_resolution` | `(prediction: Prediction, resolution: ResolutionOutcome) -> Optional[Dict]` | Verify a prediction against actual market resolution |
| `get_accuracy_stats` | `() -> Dict[str, Any]` | Get historical accuracy statistics (total, weighted, recent) |
| `format_prediction` | `(prediction: Prediction) -> str` | Format prediction for terminal display |

### `Signal`

Dataclass representing an individual prediction signal.

| Field | Type | Description |
|-------|------|-------------|
| `signal_type` | `SignalType` | Category of the signal |
| `direction` | `Direction` | Bullish, bearish, or neutral |
| `strength` | `float` | Signal strength from 0 to 1 |
| `confidence` | `float` | Confidence level from 0 to 1 |
| `value` | `float` | Raw computed signal value |
| `description` | `str` | Human-readable description |

### `Prediction`

Dataclass representing a complete market prediction with supporting signals.

| Field | Type | Description |
|-------|------|-------------|
| `market_id` | `str` | Market identifier |
| `market_title` | `str` | Display title |
| `direction` | `Direction` | Overall predicted direction |
| `probability_change` | `float` | Expected change in probability (percentage points) |
| `confidence` | `float` | Overall confidence 0-1 |
| `horizon_hours` | `int` | Prediction time horizon |
| `signals` | `List[Signal]` | Supporting signals |

### `SignalType` (Enum)

Signal categories: `MOMENTUM`, `VOLUME`, `WHALE`, `SMART_MONEY`, `ORDERBOOK`, `SENTIMENT`, `TECHNICAL`.

### `Direction` (Enum)

Prediction directions: `BULLISH`, `BEARISH`, `NEUTRAL`.

## Scoring / Algorithms

### Signal Weights

| Signal Type | Weight |
|-------------|--------|
| Momentum | 0.25 |
| Smart Money | 0.25 |
| Whale | 0.20 |
| Volume | 0.15 |
| Order Book | 0.10 |
| Technical | 0.05 |

### Momentum Signal

- **DB source**: Computes short-term (last ~6 hours, weight 0.7) and long-term (full 48h window, weight 0.3) price changes from market snapshots.
- **API source**: Weighted average of 1-day (0.5), 1-week (0.35), and 1-month (0.15) price changes.
- **Direction thresholds**: Bullish if momentum > +2%, bearish if < -2%, neutral otherwise.
- **Confidence** (DB): Scales with data availability -- `min(1.0, snapshot_count / 20)`.

### Volume Signal

- **DB source**: Splits trade history at midpoint, computes volume acceleration as `(recent - old) / old`. Direction determined by buy/sell volume ratio (1.3x threshold).
- **API source**: Compares 24h volume against estimated 30-day daily average. Volume levels: very high (>$100k), high (>$50k), moderate (>$10k), low.
- **Confidence**: 0.6 if acceleration > 0.5, else 0.4 (DB); 0.5 if volume > $10k (API).

### Whale Signal

- Queries large trades (>$10,000 notional) in last 24 hours for the target market.
- Net flow = `(buy_volume - sell_volume) / total_volume`.
- Direction thresholds: bullish if net flow > +20%, bearish if < -20%.
- Confidence scales with total volume: `min(1.0, total_volume / 100000)`.

### Smart Money Signal

- Identifies wallets with win rate >= 70% and >= 10 trades.
- Analyzes their recent trades in the target market.
- Direction thresholds: bullish if net flow > +30%, bearish if < -30%.
- Confidence based on average win rate of matched wallets.

### Technical Signal (RSI)

- **DB source**: 14-period RSI from 72 hours of market snapshots.
- **API source**: Simple overbought/oversold based on current price (>85% = bearish, <15% = bullish).
- RSI > 70: bearish (overbought). RSI < 30: bullish (oversold). Otherwise neutral.
- Fixed confidence of 0.5 (DB) or 0.4 (API).

### Signal Combination

Signals are combined via weighted scoring:
1. Each signal's direction is converted to numeric: bullish = +1, bearish = -1, neutral = 0.
2. Score = `direction * strength * weight * confidence`, summed across signals.
3. Overall direction: bullish if avg score > 0.2, bearish if < -0.2, else neutral.
4. Probability change = `avg_score * 10` (scaled to -10% to +10% range).

### Accuracy Tracking

- Maintains up to 1,000 prediction records in memory.
- Tracks simple accuracy (correct/total) and confidence-weighted accuracy.
- `verify_with_resolution()` checks predictions against YES/NO market outcomes.

## Configuration

| Constant | Default | Description |
|----------|---------|-------------|
| Signal weights | See table above | Tunable via `self.weights` dict |
| Accuracy history limit | 1,000 | Max stored prediction outcomes |
| Whale trade minimum | $10,000 | Via `Database.get_large_trades()` |
| Smart money win rate | 70% | Via `Database.get_smart_money_wallets()` |
| Smart money min trades | 10 | Minimum trades for smart money qualification |
| RSI period | 14 | Standard RSI lookback window |

## Data Sources

- **Database** (`db.database.Database`): Market snapshots, trade history, wallet data, large trades, smart money wallets
- **API data** (optional `market_data` dict): `oneDayPriceChange`, `oneWeekPriceChange`, `oneMonthPriceChange`, `volume24hr`, `volume`, `liquidity`, `outcomePrices`
- **Resolution data** (`db.models.ResolutionOutcome`): For verification against actual outcomes

## Output Format

`Prediction.to_dict()` returns:

```python
{
    'market_id': str,
    'market_title': str,
    'direction': 'bullish' | 'bearish' | 'neutral',
    'probability_change': float,  # percentage points
    'confidence': float,          # 0-1
    'horizon_hours': int,
    'signal_count': int,
    'signal_summary': {'bullish': int, 'bearish': int, 'neutral': int},
    'signals': [{'type': str, 'direction': str, 'strength': float, ...}],
    'created_at': str,  # ISO format
}
```

## External Dependencies

- `polyterm.db.database.Database`
- `polyterm.db.models` (`Trade`, `MarketSnapshot`, `Wallet`, `ResolutionOutcome`)

## Related

- CLI command: `polyterm predict --limit 10`
- TUI screen: `10/pred` (predictions)
- Interacts with: `whale_tracker.py` (whale data), `scanner.py` (market monitoring)
