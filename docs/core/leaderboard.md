# Leaderboard

> Normalize public Data API trader rankings without fabricating missing stats.

## Overview

The leaderboard module maps Polymarket Data API `/v1/leaderboard` rows into a stable PolyTerm shape. It is the source of truth for `polyterm leaderboard --source data-api`. The helper refuses types the public endpoint cannot serve, maps `vol`/`pnl` from the live payload, and leaves win rate, trade count, and average size as `None` when the API does not provide them.

This module exists so CLI and TUI surfaces cannot silently invent pseudo-addresses, 0% win rates, or a win-rate ranking that is actually profit.

## Usage

```python
from polyterm.core.leaderboard import (
    data_api_sort_by,
    normalize_leaderboard_rows,
    leaderboard_quality_flags,
)

sort_by = data_api_sort_by("profit")  # "profit"
rows = normalize_leaderboard_rows(api_rows, limit=20)
flags = leaderboard_quality_flags("data-api", "profit", rows)
```

## Key Functions

| Function | Description |
|----------|-------------|
| `data_api_sort_by(board_type)` | Map `profit`/`volume` to API sorts. `active` aliases volume. `winrate` raises `UnsupportedLeaderboardType`. |
| `normalize_leaderboard_row(row)` | Map `proxyWallet`/`pnl`/`vol` to `address`/`profit`/`volume`. Drop rows with no address. |
| `normalize_leaderboard_rows(rows, limit)` | Normalize a list and drop unusable rows. |
| `sort_traders(traders, board_type)` | Sort by an available metric. Missing values sort last. |
| `leaderboard_quality_flags(source, board_type, traders)` | Provenance flags for JSON and table notes. |
| `format_trader_label(trader)` | Short wallet plus optional `userName`. |

## Identifier and Endpoint Contract

- Endpoint: `GET https://data-api.polymarket.com/v1/leaderboard`
- Period map: `24h` → `DAY`, `7d` → `WEEK`, `30d` → `MONTH`, `all` → `ALL`
- Sort map: `profit` → `PNL`, `volume`/`active` → `VOL`
- Wallet field: `proxyWallet` (fallback `address`, `user`, `wallet`)
- Win rate is not a public leaderboard field. Agent tool `trader.leaderboard` computes closed-position win-rate evidence separately and labels it in `quality_flags`.

## Quality Flags

| Flag | Meaning |
|------|---------|
| `data_api_v1_leaderboard` | Rows came from `/v1/leaderboard` |
| `local_tracked_wallets` | Rows came from local SQLite |
| `active_ranked_by_volume` | `--type active` used volume ranking |
| `winrate_unsupported_by_public_leaderboard` | Data API source refused `--type winrate` |
| `profit_not_provided` | No row included realized profit (typical for `--source local`) |
| `win_rate_not_provided` | No row included a win-rate field |
| `trade_count_not_provided` | No row included a trade count |
| `avg_size_not_provided` | No row included average size |

## Data Sources

- Polymarket Data API `/v1/leaderboard`
- Local SQLite wallets when `--source local`

## Related

- CLI: [leaderboard](../cli/leaderboard.md)
- TUI: [leaderboard_screen](../tui/screens/leaderboard_screen.md)
- API: [data_api](../api/data_api.md)
- Agent tool: `trader.leaderboard`

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module.

When updating this feature:

- Confirm `polyterm/core/leaderboard.py` still exists.
- Keep Data API identifier and sort mapping notes current.
- Do not document fabricated win-rate or trade-count fields.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Pages that depend on live market data should name the Data API endpoint.
- New modules should have a dedicated page rather than relying only on the index.
