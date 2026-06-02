# Trade Thesis

> Explainable market-level thesis composer for PolyTerm.

## Overview

`polyterm/core/trade_thesis.py` composes market metadata, CLOB order book context, risk scoring, and local archive history into one deterministic market thesis. It exists so traders and agents can ask for one decision-support object instead of stitching together many commands.

The module is no-custody and read-only. It never places orders and never handles private keys.

## Usage

### CLI

```bash
polyterm thesis -m bitcoin --format json
polyterm thesis -m bitcoin --brief
```

### Python

```python
from polyterm.core.trade_thesis import TradeThesisEngine

engine = TradeThesisEngine()
result = engine.build("bitcoin")
```

## Output Shape

The result contains:

- `market`: input, Gamma ID, slug, condition ID, token IDs, title, probability, liquidity, volume, end date.
- `thesis`: direction, confidence, summary, evidence, risks, and next actions.
- `orderbook`: CLOB spread, best bid, best ask, and level counts where available.
- `risk`: existing PolyTerm risk assessment.
- `local_history`: recent SQLite snapshot count and probability endpoints.
- `quality_flags`: missing token IDs, unavailable order book, no execution, and related caveats.

## How It Works

The engine resolves an identifier through Gamma, extracts CLOB token IDs with `market_utils`, queries CLOB order book depth for the primary token, scores market risk with `MarketRiskScorer`, checks local snapshot history, and builds evidence and risk lists from those signals.

Confidence is intentionally explainable and conservative. It increases when probability is decisive, the order book is available, the risk grade is acceptable, and local history exists.

## Data Sources

- Gamma API for discovery and market metadata.
- CLOB API `/book` for current order book context.
- Local SQLite `market_snapshots`.
- `core/risk_score.py` for risk grading.

## Agent Notes

Agents should treat `trade_thesis` as a decision-support object, not a command to trade. The manifest marks `analytics.thesis` as read-only and non-mutating. Agents should inspect `quality_flags` before relying on the thesis.

## Verification

```bash
polyterm thesis -m bitcoin --format json
polyterm thesis -m bitcoin --brief
```

Add focused tests around market resolution, missing token IDs, unavailable CLOB order book, and local-history scoring.

## Related Features

- [Thesis CLI](../cli/thesis.md)
- [Risk Score](risk_score.md)
- [Orderbook](orderbook.md)
- [Agent Mode](../AGENT_MODE.md)
