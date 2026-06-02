# Research CLI

> Flagship one-call agent-native market research brief.

## Overview

`polyterm research` composes PolyTerm's market thesis workflow into a higher-level research brief that agents can use directly. It resolves the market through the underlying thesis engine, builds an executive brief, preserves the full thesis object, and returns workflow metadata describing which tools ran.

The command is read-only and no-custody. It never places trades, never handles private keys, and never mutates external Polymarket state.

## Usage

```bash
polyterm research --market bitcoin
polyterm research --market bitcoin --brief
polyterm research --market bitcoin --format json
polyterm research --market bitcoin --prefetch-whales --min-notional 100000 --hours 72 --limit 5 --format json
```

## Options

- `--market, -m`: market slug, URL, Gamma ID, condition ID, or search term.
- `--prefetch-whales`: run a live whale lookup first so thesis can use newly cached local trade evidence.
- `--min-notional`: minimum notional for whale prefetch, default `100000`.
- `--hours`: whale lookback window, default `72`.
- `--limit`: displayed whale result limit, default `5`.
- `--brief`: compact table output.
- `--format`: `table` or `json`.

## JSON Output

JSON mode returns:

```json
{
  "success": true,
  "research": {
    "query": "bitcoin",
    "market": {},
    "brief": {},
    "thesis": {},
    "quality_flags": ["research_brief"],
    "workflow": []
  }
}
```

## Agent Workflow

Agents should prefer `market.research` / `polyterm research --format json` when the user asks for a complete market read. Use the returned `brief` for concise answers, `thesis.evidence_sources` for citations, `quality_flags` for caveats, and `workflow` to explain which PolyTerm tools ran.

If `quality_flags` includes `whale_flow_unavailable`, rerun with `--prefetch-whales` or call `wallet.whales` separately, then run research again.

## Verification

```bash
polyterm research --market bitcoin --format json
polyterm research --market bitcoin --brief
```

## Related Features

- [Market Research Core](../core/market_research.md)
- [Trade Thesis](../core/trade_thesis.md)
- [Agent Mode](../AGENT_MODE.md)
