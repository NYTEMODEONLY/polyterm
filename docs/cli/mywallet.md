# Mywallet

> Connect your wallet and view your Polymarket activity

## Overview

Connect your wallet and view your Polymarket activity. This is a VIEW-ONLY feature - no private keys are stored or needed.

`--positions` and `--history` still read locally tracked SQLite rows. `--pnl` does not. It replays lagged Data API `/activity` cashflow (BUY, SELL, REDEEM, MERGE, SPLIT, REBATE) and marks remaining open size from Data API `/positions`. That is not `SUM(cashPnl)` and not the live CLOB fill tape.

Official lb-api `/profit` is shown as `leaderboard_profit` with `vs-leaderboard=pre-fee` when reachable. Missing or error is null plus a quality flag. The gap is not labeled as fees unless fee cashflows are actually present.

`--format json` and dry-run paths do not prompt.

Local closed-position journal remains `polyterm pnl`.

## Usage

### CLI

```bash
polyterm mywallet [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `mw`, `mywallet`, `wallet`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--address`, `-a` | string | `none` | Wallet address to view |
| `--connect`, `-c` | flag | `false` | Connect/save a wallet address |
| `--disconnect` | flag | `false` | Disconnect saved wallet |
| `--positions`, `-p` | flag | `false` | View open positions |
| `--history`, `-h` | flag | `false` | View trade history |
| `--pnl` | flag | `false` | View lagged Data API activity-cashflow P&L (not SUM(cashPnl); not live CLOB) |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm mywallet -i

# JSON output
polyterm mywallet --format json

# Connect/save a wallet address
polyterm mywallet --connect

# Activity-cashflow P&L (view-only, lagged Data API)
polyterm mywallet --pnl --address 0x0000000000000000000000000000000000000001 --format json
```

`--pnl` JSON is parseable with no Rich preamble. Required labels: `source=activity-cashflow`, `vs_leaderboard=pre-fee` (also `vs-leaderboard`), `lag=true` / `lagged=true`. Quality flags include `lagged_data_api` and never `live_data_api_trades`. Empty activity returns `pnl`/`cashflow` null rather than a synthetic P&L.

## Data Sources

- Lagged Data API `/activity` and `/positions` for `--pnl` (not live CLOB)
- Optional lb-api `GET /profit` cross-check (`vs-leaderboard=pre-fee`)
- Local SQLite database (`~/.polyterm/data.db`) for `--positions` and `--history`
- User configuration (`~/.polyterm/config.toml`) for a saved view-only address


## Related Commands

- [Portfolio](portfolio.md)
- [Position](position.md)
- [Pnl](pnl.md) (local closed-position journal; not Data API P&L)
- [Activity-cashflow P&L](../core/pnl_cashflow.md)
- [Data API lag labels](../api/data_api_lag.md)
- [Simulate](simulate.md)
- [Parlay](parlay.md)

---

*Source: `polyterm/cli/commands/mywallet.py`*
