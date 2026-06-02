# Market Research

> Flagship agent-native market research workflow for PolyTerm.

## Overview

`polyterm/core/market_research.py` exposes `MarketResearchEngine`, a deterministic composer that turns an existing trade thesis into an agent-ready research brief. It is designed as the default one-call tool for agents that need a complete, grounded read on a market.

The engine is read-only and no-custody. It does not place trades or mutate external systems. Optional whale prefetch only reads public Polymarket Data API data and writes local SQLite cache rows through the existing wallet intelligence path.

## Usage

```python
from polyterm.core.market_research import MarketResearchEngine

engine = MarketResearchEngine()
result = engine.build("bitcoin")
```

Persist to the local archive:

```python
result = engine.build("bitcoin", persist=True)
```

With live whale prefetch:

```python
result = engine.build(
    "bitcoin",
    prefetch_whales=True,
    min_notional=100000,
    hours=72,
    limit=5,
)
```

## Output Shape

The result contains:

- `query`: original market query or identifier.
- `market`: resolved market identifiers and headline metadata from the thesis.
- `brief`: headline, direction, confidence, recommendation, key evidence, key risks, gaps, and next actions.
- `thesis`: complete `TradeThesisEngine.build()` output, including `evidence_sources`.
- `quality_flags`: flattened flags beginning with `research_brief` plus thesis flags.
- `workflow`: ordered tool calls that ran, including optional `wallet.whales` prefetch and `analytics.thesis`.
- `archive`: persistence metadata with `persisted` and `brief_id`.

## How It Works

The engine optionally runs live whale prefetch to populate local cache evidence, then builds a thesis with `TradeThesisEngine`. It derives a compact research brief from the thesis evidence, risks, next actions, and quality flags while preserving the full thesis for deeper inspection. When `persist=True`, the completed research object is written to the local `research_briefs` archive for later `archive.search` queries.

## Recommendation Labels

- `research_yes`: thesis direction is `yes` with confidence at or above 60%.
- `research_no`: thesis direction is `no` with confidence at or above 60%.
- `research_neutral`: thesis is neutral or confidence is below 60%.

These labels are research recommendations, not trade execution instructions.

## Agent Notes

Agents should use this as the default high-level workflow for “research this market” prompts. Use `brief` for user-facing summaries, `thesis.evidence_sources` for citations, and `workflow` to disclose which PolyTerm tools were run. Inspect `quality_flags` before making strong claims.

## Verification

```bash
pytest tests/test_market_research.py -q
polyterm research --market bitcoin --format json
```

## Related Features

- [Research CLI](../cli/research.md)
- [Trade Thesis](trade_thesis.md)
- [Wallet Intelligence](wallet_intelligence.md)
