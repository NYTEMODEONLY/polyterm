# Archive

> Research archive snapshot collection and dataset manifest helpers.

## Overview

`ArchiveCollector` stores repeatable market snapshots and exports local dataset manifests for agent workflows.

It also exposes `search_research_briefs()` for Phase 3 agent memory: market research briefs persisted by `market.research` / `polyterm research --persist` can be searched by query, slug, title, market id, or condition id.

`status()` reports archive coverage and freshness for a query/market id, including local research brief counts, market snapshot counts, orderbook snapshot counts, price-history snapshot counts, latest timestamps, stale/missing flags, and recommended refresh actions.

When `market.research` is run with `persist=True`, it now captures a research brief plus live evidence snapshots: normalized market metadata, the thesis orderbook snapshot, and a CLOB price-history snapshot when a token id is available. Unavailable evidence is marked missing/stale by `archive.status`; PolyTerm does not synthesize replacement data.

The module writes only to PolyTerm's local SQLite database. It does not mutate Polymarket state.

## Usage

### CLI

```bash
polyterm collect -m bitcoin
polyterm collect -m bitcoin --interval 30s --duration 10m
polyterm export --dataset latest --format json
polyterm export --dataset latest --format csv
```

### Python

```python
from polyterm.core.archive import ArchiveCollector

collector = ArchiveCollector()
collector.collect_once("bitcoin")
manifest = collector.dataset_manifest("latest")
```

## Public API

| Method | Description |
|--------|-------------|
| `collect_once(market)` | Resolve and store one `MarketSnapshot`. |
| `collect_for_duration(market, interval_seconds, duration_seconds)` | Foreground loop for repeated collection. |
| `dataset_manifest(dataset)` | Return local dataset metadata and recent snapshots. |
| `export_dataset(dataset, output_format)` | Export manifest data as JSON or CSV. |

## How It Works

The collector resolves a market through Gamma, normalizes current probability with `market_utils`, builds a `MarketSnapshot`, and inserts it through `Database.insert_snapshot()`. Dataset manifests use `Database.get_database_stats()` and recent snapshots to give agents a quick inventory without reading SQLite directly.

## Data Sources

- Gamma API for market metadata.
- Local SQLite `market_snapshots`.
- Local SQLite row counts for wallets, trades, alerts, positions, bookmarks, and related tables.

## Quality Flags

Archive output includes flags such as:

- `live_gamma_snapshot`
- `missing_token_ids`
- `missing_24h_volume`
- `local_sqlite_dataset`
- `read_only_export`

These flags help researchers distinguish complete datasets from partial snapshots.

## Agent Notes

The archive is local SQLite state and never mutates external Polymarket state.
Agents should use `archive.search` before rerunning research when the user asks what PolyTerm already knows about a market. Returned briefs include the compact brief, quality flags, workflow trace, and full payload.
Agents should use `archive.status` when deciding whether local evidence is fresh enough for the user's question. `fresh`, `stale`, and `missing` statuses are computed against `max_age_hours` and never call live Polymarket APIs.

## Verification

```bash
polyterm collect -m bitcoin --format json
polyterm export --dataset latest --format json
```

Run database tests if schema or row-count behavior changes.

## Related Features

- [Collect CLI](../cli/collect.md)
- [Export CLI](../cli/export.md)
- [Database](../db/database.md)
- [Agent Mode](../AGENT_MODE.md)
