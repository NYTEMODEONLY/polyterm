# Leaderboard

> View public Polymarket Data API trader rankings (PNL / volume)

## Overview

View top traders from the public Data API `/v1/leaderboard` endpoint. Default source is live Data API rows. This command does not generate pseudo-addresses or random PnL.

The public endpoint ranks by profit (`PNL`) or volume (`VOL`). It does not provide win rate, trade count, or average size. `--type winrate` is refused on the Data API source instead of being silently mapped to profit. `--type active` is a disclosed volume ranking.

`--source local` ranks wallets already stored in local SQLite. That is not a live Polymarket ranking.

This workflow is view-only. It does not place trades or access private keys.

## Usage

### CLI

```bash
polyterm leaderboard [options]
```

### TUI

In the TUI, use shortcuts: `lb`, `leaderboard`

The TUI notes that win rate is not provided by the public leaderboard.

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type`, `-t` | ['profit', 'volume', 'winrate', 'active'] | `profit` | Ranking type. `winrate` is refused on `--source data-api`. `active` uses volume. |
| `--period`, `-p` | ['24h', '7d', '30d', 'all'] | `7d` | Time period mapped to DAY/WEEK/MONTH/ALL |
| `--limit`, `-l` | int | `20` | Number of traders to show |
| `--me` | flag | `false` | Compare local tracked positions to this board (not a live rank) |
| `--source` | ['data-api', 'local'] | `data-api` | Live Data API or local SQLite wallets |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
polyterm leaderboard
polyterm leaderboard --type volume --period 24h --format json
polyterm leaderboard --source local
polyterm leaderboard --me
```

JSON includes `source`, `endpoint`, `quality_flags`, and `win_rate: null` when the API omits win rate.

## Data Sources

- Polymarket Data API `GET /v1/leaderboard` (`proxyWallet`, `pnl`, `vol`, `userName`)
- Local SQLite (`~/.polyterm/data.db`) for `--source local` and `--me`

Identifier notes:

- Wallet field is the Data API `proxyWallet`.
- Gamma market IDs and CLOB token IDs are not used by this command.

## Related Commands

- [Follow](follow.md)
- [Wallets](wallets.md)
- [Whales](whales.md)
- Core helper: [leaderboard](../core/leaderboard.md)

---

*Source: `polyterm/cli/commands/leaderboard.py`*

## June 2026 Data API Source

`polyterm leaderboard` defaults to the public Data API. It no longer generates representative pseudo-trader data.

If the Data API leaderboard surface changes, JSON mode reports a normal error instead of inventing trader rows. Agent-native `trader.leaderboard` remains a separate tool that labels closed-position win-rate evidence in `quality_flags`.

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm the linked source file still exists.
- Update command examples, TUI shortcuts, and option names when Click routing changes.
- Keep Data API endpoint, identifier types, and omitted fields explicit.
- Run `./test_all_commands.sh` and `.venv/bin/python scripts/validate_docs.py`.
