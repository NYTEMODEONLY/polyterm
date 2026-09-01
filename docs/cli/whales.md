# Whales

> Wallet-level lagged Data API prints (`--wallets`) or Gamma 24h volume heuristic (default)

## Overview

Default `polyterm whales` lists high-volume **markets** from Gamma `volume24hr`. That path is a volume heuristic. It does not identify traders, invent addresses, or emit `trader='Volume Spike'`. JSON uses `markets` plus `evidence_level: "gamma_volume24hr_heuristic"`.

`polyterm whales --wallets` is the wallet-level print path. It reuses `PrintScanner` and reads the public Data API trade tape. JSON includes `prints` plus a wallet rollup of that tape. Those fills are lagged Data API rows (`source=data_api`, `lag=true`, `lagged=true`), not the live CLOB tape. Empty tape stays empty. This path does not score insiders, detect syndicates, or copy-trade.

`--min-notional` is an alias of `--min-amount`. Default `$10,000`, the same print floor as `polyterm watch` and `polyterm alerts` print rules.

`--local` implies wallet-level mode using only the local observed-trades database.

This workflow is view-only. `--wallets` does not write SQLite. `--local` only reads local observed trades.

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
| `--min-amount` / `--min-notional` | float | `10000` | Minimum 24h volume (heuristic) or lagged print notional (`--wallets`). Same $10k floor as watch/alerts. Not live CLOB |
| `--market` | string | `none` | Filter by market ID |
| `--hours` | int | `24` | Timestamp filter on lagged prints (`--wallets`). Does not paginate a complete historical tape |
| `--limit` | int | `20` | Maximum rows to show |
| `--wallets` | flag | `false` | Wallet-level lagged Data API prints (not live CLOB) |
| `--volume` | flag | `false` | Explicit Gamma 24h high-volume market heuristic |
| `--local` | flag | `false` | Local observed-trades database (implies `--wallets`) |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Volume heuristic (no trader identity)
polyterm whales --volume --min-amount 10000 --format json

# Wallet-level lagged Data API prints
polyterm whales --wallets --min-notional 10000 --hours 24 --format json
polyterm whales --wallets --min-notional 100000 --market bitcoin-100k
```

Default JSON (heuristic) includes `mode: "volume_heuristic"`, `evidence_level`, `disclosure`, and `markets`. It does not include a `trades` array or a `trader` field.

`--wallets` JSON includes `mode: "wallet_trades"`, `source: "data_api"`, `lag=true`, `lagged=true`, `prints`, `wallets`, and `quality_flags` containing `lagged_data_api`. It does not include `insider_score`. Quality flags never include `live_data_api_trades`.

Table `--wallets` output shows a lagged Data API banner and a print tape (time, wallet, side, notional, market). Empty tape prints that nothing matched and that empty tape is not invented whales.

## Data Sources

- Default / `--volume`: Gamma Markets REST API (`volume24hr`)
- `--wallets`: lagged Polymarket Data API `/trades` via `PrintScanner` (not live CLOB)
- `--local`: local SQLite observed trades

## Related Commands

- [Follow](follow.md)
- [Wallets](wallets.md)
- [Watch](watch.md)
- [Alerts](alerts.md)
- [Print scanner](../core/print_scanner.md)
- [Whale prints](../core/whale_prints.md)
- [Data API lag labels](../api/data_api_lag.md)

---

*Source: `polyterm/cli/commands/whales.py`*

## Wallet-Level Prints

`polyterm whales --wallets` exposes wallet-level prints from the public Polymarket Data API trade tape. It is intended for whale watchers and agents that need wallet addresses instead of only high-volume market proxies.

```bash
polyterm whales --wallets --min-notional 10000 --hours 24 --limit 5 --format json
```

The wallet mode calls `scan_whale_prints`, which uses `PrintScanner` (`filterType=CASH`, `filterAmount=<min-notional>` on the global tape). It then filters by timestamp when `--hours` is set and returns both the print tape and a wallet rollup of that tape. `--hours` does not invent a complete lookback; it drops prints older than the window when a timestamp is present.

Empty Data API pages return `prints=[]` and `wallets=[]`. Missing wallet fields are omitted from the rollup. They are not replaced with synthetic whales.

Use `--local` only when you explicitly want the local SQLite observed-trades cache:

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
- Do not document insider scoring or copy-execution on `--wallets`.
- Run `./test_all_commands.sh` and `.venv/bin/python scripts/validate_docs.py`.
