# Whales

> Wallet-level public trades (`--wallets`) or Gamma 24h volume heuristic (default)

## Overview

Default `polyterm whales` lists high-volume **markets** from Gamma `volume24hr`. That path is a volume heuristic. It does not identify traders, invent addresses, or emit `trader='Volume Spike'`. JSON uses `markets` plus `evidence_level: "gamma_volume24hr_heuristic"`.

`polyterm whales --wallets` is the wallet-level whale path. It reads the public Data API trade tape and returns real wallet addresses.

`--local` implies wallet-level mode using only the local observed-trades database.

This workflow is view-only.

## Usage

### CLI

```bash
polyterm whales [options]
polyterm whales --wallets [options]
```

### TUI

Shortcuts: `3`, `w`

The TUI screen is labeled as a high-volume market heuristic and tells users to run `polyterm whales --wallets` for trader identity.

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--min-amount` | int | `10000` | Minimum 24h volume (heuristic) or trade notional (`--wallets`) |
| `--market` | string | `none` | Filter by market ID |
| `--hours` | int | `24` | Hours of history for `--wallets` |
| `--limit` | int | `20` | Maximum rows to show |
| `--wallets` | flag | `false` | Wallet-level whale trades from the public Data API trade tape |
| `--volume` | flag | `false` | Explicit Gamma 24h high-volume market heuristic |
| `--local` | flag | `false` | Local observed-trades database (implies `--wallets`) |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Volume heuristic (no trader identity)
polyterm whales --volume --min-amount 10000 --format json

# Wallet-level public trades
polyterm whales --wallets --min-amount 100000 --hours 72 --format json
```

Default JSON (heuristic) includes `mode: "volume_heuristic"`, `evidence_level`, `disclosure`, and `markets`. It does not include a `trades` array or a `trader` field.

## Data Sources

- Default / `--volume`: Gamma Markets REST API (`volume24hr`)
- `--wallets`: Polymarket Data API `/trades`
- `--local`: local SQLite observed trades


## Related Commands

- [Follow](follow.md)
- [Wallets](wallets.md)
- [Clusters](clusters.md)
- [Attribution](attribution.md)
- [Groups](groups.md)

---

*Source: `polyterm/cli/commands/whales.py`*

## June 2026 Wallet-Level Mode

`polyterm whales --wallets` exposes wallet-level whale activity from the public Polymarket Data API trade tape. This mode is intended for whale watchers and agents that need wallet addresses instead of only high-volume market proxies.

```bash
polyterm whales --wallets --min-amount 100000 --hours 72 --limit 5 --format json
```

The wallet mode calls Data API `/trades` with `filterType=CASH` and `filterAmount=<min-amount>`, then filters by timestamp and returns both top trades and wallet rollups. Its JSON output includes wallet address, trade count, notional value, largest trade, top markets, rows/pages scanned, `cached_trade_count`, and quality flags.

Each live wallet-mode lookup also logs matching public whale trades into the local SQLite `trades` table and upserts whale wallet summaries into `wallets`. Re-running the same lookup does not duplicate rows when transaction hashes are present.

Use `--local` only when you explicitly want the older local SQLite observed-trades cache:

```bash
polyterm whales --wallets --local --min-amount 50000 --hours 24 --format json
```

`--local` without `--wallets` still selects wallet-level local data rather than the Gamma volume heuristic.

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm `polyterm/cli/commands/whales.py` still exists.
- Keep the heuristic vs `--wallets` evidence levels distinct.
- Do not document a synthetic trader identity on the volume path.
- Run `./test_all_commands.sh` and `.venv/bin/python scripts/validate_docs.py`.
