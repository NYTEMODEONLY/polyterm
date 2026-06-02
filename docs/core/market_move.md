# Market Move

> Core engine for explaining recent market price movements.

## Overview

`polyterm/core/market_move.py` exposes `MarketMoveExplainer`, a small deterministic engine that resolves a Polymarket market, fetches recent primary YES-token price history, checks current order book spread, and returns a structured explanation of the move.

The engine is read-only and no-custody. It never places trades or mutates external Polymarket state.

## Usage

```python
from polyterm.core.market_move import MarketMoveExplainer

explainer = MarketMoveExplainer()
result = explainer.explain("bitcoin", hours=24)
```

## Output Shape

The result contains:

- `query`: original user query or identifier.
- `market`: resolved Gamma ID, slug, CLOB condition ID, CLOB token IDs, title, probability, volume, and liquidity.
- `move`: direction (`up`, `down`, `flat`, or `unknown`), start/end YES prices, absolute and relative change, lookback hours, and usable price-history point count.
- `headline`: compact user-facing movement summary.
- `drivers`: deterministic evidence bullets based on price-history magnitude and order book spread.
- `caveats`: limitations such as unavailable price history or missing token IDs.
- `orderbook`: current CLOB bid/ask/spread metadata when available.
- `evidence_sources`: structured Gamma, CLOB price-history, and CLOB order-book records for agent citation.
- `quality_flags`: availability flags ending with `no_trade_execution`.

## How It Works

1. Resolve the market through Gamma; if direct lookup fails, search and prefer an active, non-closed market.
2. Extract CLOB token IDs using `api/market_utils.py` and select the primary YES token.
3. Fetch CLOB price history with `get_price_history(token_id, interval="1h", fidelity=60)`.
4. Fetch the CLOB order book with depth 20.
5. Compute direction, absolute change, relative change, drivers, caveats, evidence sources, and quality flags without using opaque model output.

## Data Sources

- Gamma API for market metadata and current probability fields.
- CLOB price history for recent YES price movement.
- CLOB order book for current bid/ask spread context.

## Verification

```bash
pytest tests/test_market_explain_move.py -q
polyterm explain-move --market bitcoin --format json
```

## Related Features

- [Explain Move CLI](../cli/explain_move.md)
- [Trade Thesis](trade_thesis.md)
- [Market Research](market_research.md)
- [CLOB API](../api/clob.md)
