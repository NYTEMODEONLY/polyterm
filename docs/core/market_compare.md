# Market Compare Core

## Overview

`polyterm/core/market_compare.py` contains `MarketComparisonEngine`, the agent-native comparison engine behind `market.compare`. It resolves two or more market identifiers, summarizes current YES probabilities, recent CLOB price movement, order-book spread context, and pairwise divergence metrics.

## Source Path

- `polyterm/core/market_compare.py`

## Data Sources

- Gamma Markets API for market metadata, Gamma market IDs, slugs, questions, liquidity, volume, condition IDs, and CLOB token IDs.
- CLOB price history API for recent YES move summaries.
- CLOB order-book API for current bid/ask spread context.

## Identifier Requirements

Inputs are market identifiers or search terms. The engine resolves each input independently:

- Gamma market IDs and Gamma slugs are used for metadata resolution.
- CLOB condition IDs identify CLOB markets once resolved from Gamma metadata.
- CLOB token IDs identify YES/NO tokens; `market.compare` uses the first token ID as the YES-side token for price history and order-book reads.

When identifiers are ambiguous, agents should call `market.resolve` or `market.search` first.

## Output Contract

`market.compare` returns the standard PolyTerm envelope. The `data` payload includes:

- `markets`: per-market identifiers, title, probability, liquidity, volume, recent move, and order-book context.
- `pairwise`: probability, liquidity, volume, and combined-probability gaps for every market pair.
- `divergence_summary`: widest probability gap and notable pairs.
- `evidence_sources`: Gamma and CLOB source availability.
- `quality_flags`: warnings such as `need_at_least_two_markets`, `price_history_unavailable`, or `orderbook_unavailable`.

The tool is read-only and no-custody; it cannot place trades.

## Verification

```bash
pytest tests/test_market_compare.py tests/test_market_compare_agent.py -q
printf '{"tool":"market.compare","args":{"markets":["bitcoin 100k","bitcoin 90k"],"hours":24}}\n' | polyterm agent jsonl-server
polyterm agent schemas market.compare --format json
```

## Related Documentation

- [Compare CLI](../cli/compare.md)
- [Agent Mode](../AGENT_MODE.md)
- [Market Move Core](market_move.md)
- [Gamma API](../api/gamma.md)
- [CLOB API](../api/clob.md)
