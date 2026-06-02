# Thesis

> Explainable market-level trade thesis for traders, researchers, and agents.

## Overview

`polyterm thesis` combines market metadata, CLOB identifiers, current probability, order book shape, risk scoring, and local historical evidence into one market-level thesis. The output is designed for terminal users and agent runtimes that need a compact decision object with evidence and caveats.

The command is read-only. It does not submit orders, manage keys, or mutate local state except for normal API client caching outside the command surface.

## Usage

### CLI

```bash
polyterm thesis --market "bitcoin" --brief
polyterm thesis -m "will-bitcoin-hit-100k" --format json
```

### TUI

There is no dedicated TUI screen yet. Future TUI work can route to this command because the command has a stable JSON mode and compact table mode.

## Options / Parameters

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | required | Market slug, URL, Gamma ID, condition ID, token ID, or search term. |
| `--brief` | boolean | false | Print a compact one-screen thesis. |
| `--format` | choice | `table` | Use `json` for agent and script output. |

## Examples

```bash
# One-screen terminal summary
polyterm thesis -m "bitcoin" --brief

# Agent-safe JSON
polyterm thesis -m "bitcoin" --format json

# Use a Polymarket slug
polyterm thesis -m "will-bitcoin-hit-100k" --format json
```

## How It Works

The command instantiates `TradeThesisEngine` from `polyterm/core/trade_thesis.py`. The engine resolves the market through Gamma, extracts CLOB token IDs with `market_utils`, probes the CLOB order book when a token ID is available, scores market risk with `MarketRiskScorer`, and checks local snapshot history in SQLite.

It then builds a deterministic thesis object with direction, confidence, evidence, risks, next actions, quality flags, and current market identifiers.

## Data Sources

- Gamma API for market metadata, slug lookup, and current probability fields.
- CLOB API for order book bids, asks, and spread.
- Local SQLite snapshots for recent archive evidence.
- Existing risk scoring logic in `core/risk_score.py`.

## Identifier Requirements

Gamma market IDs and slugs are used for discovery. CLOB condition IDs and CLOB token IDs are used for order book context. The JSON output includes all identifiers found so agents can pass the right ID to downstream tools.

## Agent Workflow

Agents should call `polyterm thesis --format json` after resolving a market and before deciding whether to run deeper wallet, order book, or archive tools. The command is marked read-only in the agent manifest.

## Verification

```bash
polyterm thesis -m bitcoin --brief
polyterm thesis -m bitcoin --format json
```

Run focused tests for `core/trade_thesis.py` and command smoke after implementation changes.

## Related Features

- [Agent](agent.md)
- [Risk](risk.md)
- [Orderbook](orderbook.md)
- [Whales](whales.md)
- [Trade Thesis Core](../core/trade_thesis.md)
