# Alert Engine

> Unified local alert rule evaluation for PolyTerm.

## Overview

`polyterm/core/alert_engine.py` provides local alert rule creation and one-shot evaluation. It supports agent-safe creation of local price rules and scheduled scan workflows without adding external custody or trading behavior.

The module mutates local state when a rule is saved or when a triggered alert is inserted. It never mutates Polymarket state.

## Usage

### CLI

```bash
polyterm alerts --add-rule price --market bitcoin --above 0.70 --format json
polyterm alerts --add-rule price --market bitcoin --above 0.70 --dry-run
polyterm watch --market bitcoin --schedule 15m --runs 1 --format json
```

### Python

```python
from polyterm.core.alert_engine import AlertEngine

engine = AlertEngine()
rule = engine.create_price_rule("bitcoin", above=0.70)
scan = engine.run_once("bitcoin", above=0.70)
```

## Public API

| Method | Description |
|--------|-------------|
| `create_price_rule(market, above, below, severity, dry_run)` | Save or preview a local price rule. |
| `run_once(market, above, below)` | Evaluate a transient price rule and insert an alert if triggered. |

## How It Works

The engine resolves a market through Gamma, reads the current probability, and compares it with `above` and `below` thresholds. Saved rules are currently stored in the existing `price_alerts` table. One-shot triggered events are inserted into the existing `alerts` table.

This first implementation focuses on price rules and scheduled scans. The module is structured so whale, volume, new-market, resolution, and risk-change rules can be added without changing command ownership.

## Data Sources

- Gamma API for market metadata and current probability.
- Local SQLite `price_alerts` for saved rules.
- Local SQLite `alerts` for triggered event records.

## Agent Safety

`alerts.create_price_rule` is marked as local-state mutation in the agent manifest. Agents can call `--dry-run` first to preview a rule without changing local state.

## Verification

```bash
polyterm alerts --add-rule price --market bitcoin --above 0.70 --dry-run --format json
polyterm watch --market bitcoin --format json
```

Run alert CLI and core tests after adding new rule types.

## Related Features

- [Alerts CLI](../cli/alerts.md)
- [Watch CLI](../cli/watch.md)
- [Notifications](notifications.md)
- [Agent Mode](../AGENT_MODE.md)
