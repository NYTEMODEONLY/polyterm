# Fee Calculations

> CLOB V2 protocol fee schedule parsing and trade fee estimation.

## Overview

The fees module centralizes PolyTerm's protocol fee calculations for CLOB V2. It parses fee schedules from Gamma market metadata, reads CLOB fee-rate responses, and estimates taker fees using the CLOB V2 fee curve. This replaces the old fixed global 2% assumption in user-facing trade tools.

## Key Classes and Functions

### `FeeSchedule`

Dataclass describing a fee schedule.

| Field | Type | Description |
|-------|------|-------------|
| `rate` | `float` | Base fee rate as a decimal |
| `exponent` | `float` | Curve exponent applied to `price * (1 - price)` |
| `source` | `str` | Source label, such as `market`, `clob`, `generic`, or `zero` |

### Functions

| Function | Description |
|----------|-------------|
| `fee_schedule_from_market(market)` | Parse Gamma market fee metadata such as `feeSchedule`, `feesEnabled`, or legacy `takerBaseFee` fields |
| `fee_schedule_from_clob_fee_rate(response)` | Parse CLOB `/fee-rate` response metadata |
| `effective_taker_fee_rate(price, schedule)` | Calculate the effective taker fee rate at a given price |
| `estimate_taker_fee(amount, price, schedule)` | Estimate protocol fee in dollars for a trade amount |
| `breakeven_price(price, schedule)` | Estimate breakeven price after protocol fee |
| `fee_source_label(schedule)` | Return a human-readable source label for display and JSON output |

## Fee Curve

The current estimate uses:

```python
effective_rate = schedule.rate * (price * (1 - price)) ** schedule.exponent
fee = amount * effective_rate
```

The curve is price-sensitive: fees are generally highest near 50/50 markets and lower near the extremes. When a market does not expose fee metadata, PolyTerm uses a generic protocol estimate and labels the source accordingly.

## Consumers

- `polyterm fees`
- `polyterm trade`
- `polyterm quicktrade`

These commands report the fee source used for each estimate so users can distinguish market-sourced schedules from generic fallback estimates.

## Related

- API client: `polyterm.api.clob.CLOBClient.get_fee_rate`
- CLI commands: `fees`, `trade`, `quicktrade`
