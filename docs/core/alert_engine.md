# Alert Engine

> Unified local alert rule evaluation for PolyTerm.

## Overview

`polyterm/core/alert_engine.py` provides local alert rule creation and one-shot evaluation. It supports agent-safe creation of local price rules, print rules on lagged Data API fills, and scheduled scan workflows without adding external custody or trading behavior.

The module mutates local state when a rule is saved or when a triggered alert is inserted. It never mutates Polymarket state. Print evaluation is lagged Data API, not live CLOB. `polyterm watch` reuses `PrintScanner` in the same process; this engine still owns one-shot price and print rule evaluation.

## Usage

### CLI

```bash
polyterm alerts --add-rule price --market bitcoin --above 0.70 --format json
polyterm alerts --add-rule price --market bitcoin --above 0.70 --dry-run
polyterm alerts --add-rule print --min-notional 10000 --dry-run --format json
polyterm alerts --evaluate print --min-notional 10000 --format json
polyterm watch --market bitcoin --schedule 15m --runs 1 --format json
```

### Python

```python
from polyterm.core.alert_engine import AlertEngine

engine = AlertEngine()
rule = engine.create_price_rule("bitcoin", above=0.70)
scan = engine.run_once("bitcoin", above=0.70)
print_rule = engine.create_print_rule(min_notional=10000, dry_run=True)
prints = engine.run_print_once(min_notional=10000, dry_run=True)
```

## Public API

| Method | Description |
|--------|-------------|
| `create_price_rule(market, above, below, severity, dry_run)` | Save or preview a local price rule. |
| `create_print_rule(min_notional, market, wallet, severity, dry_run)` | Save or preview a local print rule. Dry-run does not write SQLite. |
| `run_once(market, above, below, dry_run)` | Evaluate a transient price rule. Inserts an alert if triggered unless `dry_run`. |
| `run_print_once(min_notional, market, wallet, limit, dry_run)` | Evaluate lagged Data API prints. Inserts `alert_type=print` rows unless `dry_run`. |

## How It Works

Price rules resolve a market through Gamma, read the current probability, and compare it with `above` and `below` thresholds. Saved price rules still use the `price_alerts` table.

Print rules do not use Gamma. `PrintScanner` reads Data API `/trades`, drops non-trade rows, and matches min notional plus optional market/wallet filters. Saved print rules use the `alert_rules` table. Fired prints are `alerts.alert_type=print` with lagged Data API labels. `polyterm watch` still calls `run_once` (price). Run prints with `polyterm alerts --evaluate print`.

The module is structured so whale, volume, new-market, resolution, and risk-change rules can be added without changing command ownership.

## Data Sources

- Gamma API for market metadata and current probability (price rules).
- Data API `/trades` via `PrintScanner` for verified prints (lagged, not live CLOB).
- Local SQLite `price_alerts` for saved price rules.
- Local SQLite `alert_rules` for saved print rules.
- Local SQLite `alerts` for triggered event records.

## Agent Safety

`alerts.create_price_rule` is marked as local-state mutation in the agent manifest. Agents can call `--dry-run` first to preview a rule without changing local state.

## Verification

```bash
polyterm alerts --add-rule price --market bitcoin --above 0.70 --dry-run --format json
polyterm alerts --evaluate print --min-notional 10000 --dry-run --format json
polyterm watch --market bitcoin --format json
```

Run alert CLI and core tests after adding new rule types.

```bash
.venv/bin/python -m pytest tests/test_core/test_alert_engine.py tests/test_core/test_print_scanner.py tests/test_cli/test_alerts.py
```

## Related Features

- [Alerts CLI](../cli/alerts.md)
- [Print scanner](print_scanner.md)
- [Watch CLI](../cli/watch.md)
- [Notifications](notifications.md)
- [Data API lag labels](../api/data_api_lag.md)
- [Agent Mode](../AGENT_MODE.md)
