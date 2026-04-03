# Rewards

> Holding and liquidity rewards calculator for Polymarket positions.

## Overview

The rewards module estimates Polymarket's 4% APY holding rewards on qualifying positions and analyzes liquidity provision reward eligibility. It provides daily, weekly, monthly, and yearly reward projections and determines which positions qualify based on price range and hold duration criteria.

## Key Classes and Functions

### `RewardsCalculator`

Calculates estimated holding rewards and liquidity provision eligibility.

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `is_position_qualifying` | `(price: float, hold_hours: Optional[float] = None) -> bool` | Check if a position meets holding reward criteria |
| `estimate_holding_rewards` | `(positions: List[Dict]) -> Dict[str, Any]` | Estimate rewards for a list of positions |
| `estimate_liquidity_rewards` | `(open_orders: List[Dict]) -> Dict[str, Any]` | Estimate liquidity provision reward eligibility |
| `calculate_effective_yield` | `(position_value: float, holding_days: int) -> Dict[str, Any]` | Calculate effective yield including holding rewards |

## Scoring / Algorithms

### Holding Rewards

Polymarket offers 4% APY on qualifying positions. The daily rate is computed as:

```
daily_rate = 0.04 / 365
```

A position qualifies if:
- Entry price is between $0.20 and $0.80 (near the midpoint, not near-certain outcomes)
- Position has been held for at least 24 hours

Reward projections:
- **Daily**: `qualifying_value * daily_rate`
- **Weekly**: `daily * 7`
- **Monthly**: `daily * 30`
- **Yearly**: `qualifying_value * 0.04`

### Liquidity Rewards

Orders are eligible for liquidity rewards if:
- Order is within **5 cents** of the market midpoint
- Order value is at least **$10** (`price * size >= 10`)

The closer an order is to the midpoint, the higher the potential reward.

### Effective Yield

For a given position value and holding period:
- `total_reward = position_value * daily_rate * holding_days`
- `effective_apy = (total_reward / position_value) * (365 / holding_days)`

## Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `HOLDING_APY` | 0.04 | 4% annual percentage yield |
| `DAILY_RATE` | ~0.0001096 | APY / 365 |
| `QUALIFYING_MIN` | 0.20 | Minimum price for qualifying positions |
| `QUALIFYING_MAX` | 0.80 | Maximum price for qualifying positions |
| `MIN_HOLD_HOURS` | 24 | Minimum hold duration in hours |

## Data Sources

- Position data is passed in as parameters (list of dicts with `value`, `price`, `hold_hours`)
- Open order data is passed in as parameters (list of dicts with `price`, `size`, `side`, `market_midpoint`)
- No direct API or database dependencies

## Output Format

### `estimate_holding_rewards()` returns:

```python
{
    'qualifying_positions': int,
    'non_qualifying_positions': int,
    'total_qualifying_value': float,
    'estimated_daily': float,
    'estimated_weekly': float,
    'estimated_monthly': float,
    'estimated_yearly': float,
    'apy': 0.04,
}
```

### `estimate_liquidity_rewards()` returns:

```python
{
    'eligible_orders': int,
    'total_order_value': float,
    'avg_distance_from_mid': float,
    'eligible': bool,
    'note': str,
}
```

### `calculate_effective_yield()` returns:

```python
{
    'total_reward': float,
    'effective_apy': float,
    'daily_reward': float,
    'holding_days': int,
    'position_value': float,
}
```

## External Dependencies

- None (standalone calculations, no external imports beyond stdlib)

## Related

- CLI command: `polyterm rewards -w 0xABC...`
- TUI screen: `rw` (rewards)
- Interacts with: `mywallet.py` (wallet positions for input data)
