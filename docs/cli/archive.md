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
```

## Options

- `--query`: optional search term matching original query, market slug, title, Gamma market id, or condition id.
- `--limit`: maximum archived briefs to return, default `20`.
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

## Agent Notes

Agents should call `archive.search` before rerunning expensive or live workflows when the user asks what PolyTerm already knows about a market. Use archived `brief`, `quality_flags`, `workflow`, and `payload` fields to compare prior and current research.

Because archive rows are local evidence, agents should cite them as prior PolyTerm research, not as live market state. Re-run `market.research` when freshness matters.

## Related Features

- [Market Research](research.md)
- [Market Research Core](../core/market_research.md)
- [Research Archive Core](../core/archive.md)
