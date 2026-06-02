# Archive CLI

> Inspect PolyTerm's local research archive.

## Overview

`polyterm archive` exposes read-only local archive inspection commands for agents and humans. The current flagship subcommand is `archive search`, which searches market research briefs persisted by `polyterm research --persist` or `market.research` with `persist=true`.

The archive is local SQLite state. It does not mutate Polymarket and does not require credentials.

## Usage

```bash
polyterm archive search
polyterm archive search --query bitcoin
polyterm archive search --query bitcoin --limit 5 --format json
polyterm archive status --query bitcoin --format json
polyterm archive status --query bitcoin --market-id 2362221 --max-age-hours 24 --format json
```

## Options

### `archive search`

- `--query`: optional search term matching original query, market slug, title, Gamma market id, or condition id.
- `--limit`: maximum archived briefs to return, default `20`.
- `--format`: `table` or `json`.

### `archive status`

- `--query`: optional search term matching archived briefs.
- `--market-id`: optional resolved market id for snapshot lookup.
- `--max-age-hours`: freshness threshold, default `24`.
- `--format`: `table` or `json`.

## JSON Output

```json
{
  "success": true,
  "archive": {
    "success": true,
    "query": "bitcoin",
    "count": 1,
    "briefs": [],
    "quality_flags": ["research_brief_archive", "local_sqlite_dataset", "read_only_export"]
  }
}
```

Status output adds local evidence counts and freshness:

```json
{
  "success": true,
  "archive": {
    "success": true,
    "evidence_counts": {
      "research_briefs": 1,
      "market_snapshots": 1,
      "orderbook_snapshots": 1,
      "price_history_snapshots": 1
    },
    "freshness": {
      "research_briefs": {"status": "fresh"},
      "market_snapshots": {"status": "fresh"},
      "orderbook_snapshots": {"status": "fresh"},
      "price_history_snapshots": {"status": "fresh"}
    },
    "recommended_actions": []
  }
}
```

## Agent Notes

Agents should call `archive.status` first when freshness matters. If it reports stale or missing evidence, follow `recommended_actions` before treating archive evidence as current. Call `archive.search` when the user asks what PolyTerm already knows about a market. Use archived `brief`, `quality_flags`, `workflow`, and `payload` fields to compare prior and current research.

Because archive rows are local evidence, agents should cite them as prior PolyTerm research, not as live market state. Re-run `market.research` when freshness matters.

## Related Features

- [Market Research](research.md)
- [Market Research Core](../core/market_research.md)
- [Research Archive Core](../core/archive.md)
