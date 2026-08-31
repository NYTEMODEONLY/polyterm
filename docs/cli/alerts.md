# Alerts

> View fired alerts and manage local price and print rules.

## Overview

`polyterm alerts` lists local SQLite alerts, acknowledges them, tests notification channels, and creates local rules. Price rules compare Gamma probability to `--above` / `--below`. Print rules fire when a verified Data API fill meets a minimum notional.

A print is a trade that actually happened. Verified prints come from Polymarket's public Data API trade surface. Those fills are lagged Data API rows, not the live CLOB tape. PolyTerm does not invent wallets, notionals, prices, or a lag duration.

This command can mutate local SQLite state when a rule is saved or when evaluation stores a fired alert. It never places orders.

## Usage

### CLI

```bash
polyterm alerts [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `12`, `alert`

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | `all`, `whale`, `insider`, `arbitrage`, `smart_money`, `print` | `all` | Filter by alert type |
| `--limit` | int | `20` | Maximum alerts to show, or max matching prints when evaluating |
| `--unread` | flag | `false` | Show only unacknowledged alerts |
| `--ack` | int | `none` | Acknowledge alert by ID |
| `--add-rule` | `price`, `print` | `none` | Create a local alert rule |
| `--evaluate` | `price`, `print` | `none` | Evaluate a rule once without requiring a saved rule |
| `--market` | string | `none` | Required for price rules. Optional market filter for print rules |
| `--above` | float | `none` | Trigger price rule at or above this probability |
| `--below` | float | `none` | Trigger price rule at or below this probability |
| `--min-notional` | float | `none` | Required for print rules. Minimum verified-print notional |
| `--wallet` | string | `none` | Optional wallet filter for a print rule |
| `--dry-run` | flag | `false` | Preview create or evaluate without mutating SQLite |
| `--test-telegram` | flag | `false` | Send test Telegram notification |
| `--test-discord` | flag | `false` | Send test Discord notification |
| `--format` | `table`, `json` | `table` | Output format |

JSON and `--dry-run` paths do not prompt.

## Examples

```bash
# List recent alerts
polyterm alerts

# JSON list
polyterm alerts --format json

# Preview a print rule without writing SQLite
polyterm alerts --add-rule print --min-notional 10000 --dry-run --format json

# Save a print rule
polyterm alerts --add-rule print --min-notional 10000 --market bitcoin-100k --wallet 0xabc

# Evaluate once against lagged Data API fills (no saved rule required)
polyterm alerts --evaluate print --min-notional 10000 --format json
polyterm alerts --evaluate print --min-notional 10000 --dry-run --format json

# Price rule (existing)
polyterm alerts --add-rule price --market bitcoin --above 0.70 --dry-run --format json
```

`--evaluate print` is the scan path traders and agents can run. `polyterm watch` still evaluates Gamma price rules only.

## Print rule honesty

Print JSON includes `source=data_api`, `lag=true`, `lagged=true`, and `quality_flags` containing `lagged_data_api`. It never sets `live_data_api_trades`. Table titles use `— lagged Data API (not live CLOB)`.

Empty Data API tape returns `triggered=false` and `prints=[]`. Request errors are reported (`success=false` in JSON). Missing wallet, side, size, or price fields are omitted or marked unknown. They are not invented.

`--dry-run` on `--add-rule print` does not insert `alert_rules` rows. `--dry-run` on `--evaluate print` does not insert `alerts` rows.

## Data Sources

- Local SQLite (`~/.polyterm/data.db`): `alerts`, `alert_rules`, `price_alerts`
- User configuration (`~/.polyterm/config.toml`) for notification tests
- Print evaluate: Data API `GET /trades` via `PrintScanner` (lagged, not live CLOB)
- Price create/evaluate: Gamma market metadata and probability

## Related Commands

- [Print scanner](../core/print_scanner.md)
- [Alert engine](../core/alert_engine.md)
- [Watch](watch.md)
- [Pricealert](pricealert.md)
- [Whales](whales.md)
- [Notify](notify.md)

---

*Source: `polyterm/cli/commands/alerts.py`*

## Agent Safety

Rule creation mutates local SQLite. The agent manifest marks `alerts.create_price_rule` as `mutates_local_state: true`. Print rules are CLI-first (`--add-rule print` / `--evaluate print`). Use `--dry-run` to preview without changing local state.
