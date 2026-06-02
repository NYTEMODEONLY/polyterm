# Explain Move

> Recent YES price movement explanation for one Polymarket market.

## Overview

`polyterm explain-move` resolves a market, fetches the primary CLOB YES token price history, checks the current order book, and returns a deterministic explanation of the latest move. It is designed for agent workflows that need a quick answer to “why did this market move?” without placing trades or mutating external state.

The workflow is read-only and no-custody. It cannot submit orders, hold keys, approve contracts, or mutate Polymarket state.

## Usage

### CLI

```bash
polyterm explain-move --market "bitcoin" --brief
polyterm explain-move -m "will-bitcoin-hit-100k" --hours 12 --format json
```

### TUI

There is no dedicated TUI screen yet. The command is available through the CLI and agent adapters.

## Options / Parameters

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | required | Market slug, URL, Gamma ID, condition ID, token ID, or search term. |
| `--hours` | integer | `24` | Price-history lookback window to explain. |
| `--brief` | boolean | false | Print a compact one-screen explanation. |
| `--format` | choice | `table` | Use `json` for agent and script output. |

## Output Modes

- `table`: human-readable panel with direction, headline, drivers, caveats, and quality flags.
- `json`: script-safe object shaped as `{ "success": true, "explain_move": ... }`.

## Data Sources

- Gamma API for market metadata, Gamma market IDs, Gamma slugs, CLOB condition IDs, and CLOB token IDs.
- CLOB `prices-history` for primary YES token history.
- CLOB order book for current best bid/ask and spread context.

## Identifier Requirements

Gamma market IDs and Gamma slugs are used for discovery and metadata. CLOB condition IDs identify CLOB markets. CLOB token IDs identify YES/NO order-book and price-history tokens. `explain-move` resolves the user-provided identifier before choosing the primary YES CLOB token ID.

## Agent Workflow

Agents can call the equivalent tool as `market.explain_move` after `market.resolve` or when a user asks why a price changed. Use `drivers` for user-facing reasons, `caveats` and `quality_flags` to qualify the answer, and `evidence_sources` for citations. If `price_history_unavailable` appears, avoid attributing a move and fall back to order book / thesis / archive tools.

## Verification

```bash
pytest tests/test_market_explain_move.py tests/test_market_explain_move_agent.py -q
polyterm explain-move -m bitcoin --hours 24 --format json
```

## Related Features

- [Agent](agent.md)
- [Thesis](thesis.md)
- [Chart](chart.md)
- [Orderbook](orderbook.md)
- [Market Move Core](../core/market_move.md)
