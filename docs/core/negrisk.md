# NegRisk Multi-Outcome Arbitrage Detection

> Detects arbitrage opportunities in multi-outcome NegRisk markets where the sum of all outcome YES prices deviates from $1.00.

## Overview

In NegRisk markets, multiple outcomes are mutually exclusive (e.g., "Who wins the election?" with 5+ candidates). The sum of all YES prices should theoretically equal $1.00. When the sum is less than $1.00, buying all outcomes guarantees a profit on resolution. This module finds such mispriced events, calculates fee-adjusted profit, and returns opportunities ranked by profitability.

## Key Classes and Functions

### `NegRiskAnalyzer`

Main class for scanning multi-outcome events and detecting arbitrage.

**Constructor**: `__init__(self, gamma_client, clob_client=None, polymarket_fee=0.02)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gamma_client` | `GammaClient` | required | Gamma REST API client for fetching markets |
| `clob_client` | `CLOBClient` | `None` | Optional CLOB client (unused currently) |
| `polymarket_fee` | `float` | `0.02` | Taker fee on winnings (2%) |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `find_multi_outcome_events` | `(limit: int = 50) -> List[dict]` | Finds events with 3+ outcome markets (NegRisk candidates). Handles both nested event payloads and flat Gamma `/markets` rows by grouping markets by event. |
| `analyze_event` | `(event: dict) -> Optional[dict]` | Analyzes a single multi-outcome event for arbitrage. Returns spread, fee-adjusted profit, and outcome details. |
| `scan_all` | `(min_spread: float = 0.02) -> List[dict]` | Scans all NegRisk events, filters by minimum spread, and returns opportunities sorted by profit potential (descending). |
| `_extract_event_reference` | `(market: dict) -> Tuple[Optional[str], dict]` | Extracts event key and metadata from a flat market row, handling multiple field naming conventions. |
| `_extract_token_id` | `(market: dict) -> str` | Extracts first CLOB token ID from a market dict, parsing JSON strings if necessary. |

## Scoring / Algorithms

### Arbitrage Detection Logic

1. **Sum all YES prices** across outcomes in the event.
2. **Calculate spread**: `abs(1.0 - total_yes_price)`.
3. **Classify type**:
   - `total_yes < 1.0` = "underpriced" (buy-all arbitrage opportunity)
   - `total_yes > 1.0` = "overpriced" (potential short opportunity)
4. **Fee-adjusted profit** (for underpriced case):
   - Raw profit: `1.0 - total_yes`
   - Fee: `2% * (1.0 - cheapest_outcome_price)` (worst-case fee on the winning outcome)
   - Net profit: `raw_profit - fee`
5. **Minimum spread filter**: Default 2% (`min_spread=0.02`). Events below this threshold are excluded.

### Profit Calculation Example

For 5 outcomes summing to $0.95:
- Cost to buy all YES: $0.95
- Guaranteed return: $1.00
- Raw profit: $0.05
- Fee (2% on winning): ~$0.02 (varies by cheapest outcome)
- Net profit: ~$0.03 per dollar set

## Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| Default fee | `0.02` (2%) | Polymarket taker fee on winnings |
| Min outcomes | `3` | Minimum markets to qualify as multi-outcome |
| Market fetch limit | `limit * 3` | Fetches 3x the event limit to ensure enough grouping |
| Default event limit | `50` | Max events to scan |

## Data Sources

- **Gamma REST API**: Fetches active, non-closed markets via `GammaClient.get_markets()`
- Market outcome prices from `outcomePrices` field (JSON array or string)

## Output Format

`analyze_event()` returns a dict:

```python
{
    'event_title': str,           # Event name
    'event_id': str,              # Event identifier
    'num_outcomes': int,          # Number of outcomes
    'total_yes_price': float,     # Sum of all YES prices (rounded to 4 decimals)
    'spread': float,              # Absolute deviation from $1.00
    'type': str,                  # 'underpriced' or 'overpriced'
    'fee_adjusted_profit': float, # Net profit per $1.00 set
    'profit_per_100': float,      # Net profit per $100 invested
    'outcomes': [                 # Individual outcome details
        {
            'question': str,      # Outcome label (truncated to 60 chars)
            'yes_price': float,
            'market_id': str,
            'token_id': str,
        }
    ],
    'timestamp': str,             # ISO format timestamp
}
```

`scan_all()` returns a list of these dicts sorted by `fee_adjusted_profit` descending.

## External Dependencies

- `polyterm.api.gamma.GammaClient` -- market data fetching
- `polyterm.utils.json_output.safe_float` -- safe float parsing

## Related

- CLI command: `polyterm negrisk --min-spread 0.03`
- TUI screen: shortcut `nr`
- Related modules: `polyterm/core/arbitrage.py` (intra-market and cross-platform arbitrage)
