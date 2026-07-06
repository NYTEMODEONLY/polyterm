# Agent Cookbook

This cookbook shows practical PolyTerm workflows for agents and scripted
research. All examples use JSON output or MCP-equivalent tool names.

## Diagnose Setup

Start with a bounded local diagnostic:

```bash
polyterm agent doctor --skip-network --format json
```

Use the full diagnostic when live API connectivity matters:

```bash
polyterm agent doctor --format json
```

Read `data.summary.status`. Treat `error` as an installation problem. Treat
`warn` as usable with caveats, usually because a live API check failed.

## Research A Market

```bash
polyterm research --market "bitcoin" --persist --format json
```

Use the returned brief, evidence sources, risks, gaps, and next actions. When
`archive.captured_evidence` is present, local archive freshness can be checked
later with `archive.status`.

MCP equivalent:

```json
{
  "tool": "market.research",
  "args": {
    "market": "bitcoin",
    "persist": true
  }
}
```

## Explain A Move

```bash
polyterm explain-move --market "bitcoin" --hours 24 --format json
```

Use this when a user asks why a price moved. Prefer fields in
`evidence_sources`, `move`, `orderbook`, and `quality_flags` over unsupported
claims.

MCP equivalent:

```json
{
  "tool": "market.explain_move",
  "args": {
    "market": "bitcoin",
    "hours": 24
  }
}
```

## Compare Markets

```bash
polyterm compare -m "bitcoin 100k" -m "bitcoin 90k" --hours 24 --format json
```

Use comparison output when the task is to identify divergence, relative
mispricing, liquidity differences, or inconsistent movement across related
markets.

MCP equivalent:

```json
{
  "tool": "market.compare",
  "args": {
    "markets": ["bitcoin 100k", "bitcoin 90k"],
    "hours": 24
  }
}
```

## Scan For Opportunities

```bash
polyterm scan-opportunities --query crypto --limit 10 --min-volume 5000 --format json
```

Use `scan.opportunities` to build a research queue. It ranks fresh movers,
markets with volume/liquidity signals, and markets where local archive coverage
is stale or missing.

Next step for a promising result:

```bash
polyterm research --market "<slug-or-title>" --persist --format json
```

## Inspect Whales

```bash
polyterm whales --wallets --min-amount 100000 --hours 72 --limit 10 --format json
```

Use this before drawing conclusions from whale flow. The Data API trade tape is
public and bounded; read `quality_flags` for pagination and freshness caveats.
Filter returned trades by the relevant market slugs/outcomes before making a
claim about who whales favor.

For deterministic top-trade rankings:

```bash
printf '{"tool":"wallet.whale_trades","args":{"hours":48,"limit":5,"min_notional":10000,"sample_size":3000}}\n' | polyterm agent jsonl-server
```

Report `rows_scanned`, `pages_scanned`, `errors`, and `quality_flags`. If the
Data API times out and zero rows are scanned, retry with a smaller `sample_size`
or lower `min_notional`; if it still fails, say whale tape is unavailable.

For locally identified high win-rate wallets:

```bash
polyterm wallets --type smart --min-win-rate 0.7 --min-trades 10 --format json
```

MCP equivalents:

```json
{"tool": "wallet.whales", "args": {"min_notional": 100000, "hours": 72, "limit": 10}}
{"tool": "wallet.smart_money", "args": {"min_win_rate": 0.7, "min_trades": 10, "limit": 20}}
```

## Archive And Refresh Evidence

Check whether local evidence is fresh:

```bash
polyterm archive status --query bitcoin --max-age-hours 24 --format json
```

If `recommended_actions` asks for a refresh, run:

```bash
polyterm research --market "bitcoin" --persist --format json
```

Search prior research:

```bash
polyterm archive search --query bitcoin --limit 5 --format json
```

## Resolve Ambiguous Identifiers

When a user gives a URL, slug, Gamma ID, condition ID, or token ID:

```bash
polyterm lookup "<identifier>" --format json
```

MCP equivalent:

```json
{"tool": "market.resolve", "args": {"identifier": "<identifier>"}}
```

Use the returned Gamma market ID, slug, condition ID, and CLOB token IDs in the
appropriate follow-up tool.

## Create A Local Price Alert

This mutates local SQLite state:

```bash
polyterm alerts --add-rule price --market "bitcoin" --above 0.7 --format json
```

Agents should require policy approval before calling the MCP tool:

```json
{
  "tool": "alerts.create_price_rule",
  "args": {
    "market": "bitcoin",
    "above": 0.7
  }
}
```

PolyTerm creates a local alert rule only. It does not place orders or touch
funds.

## Good Agent Pattern

For market research tasks, a robust sequence is:

1. Run `market.resolve` when the identifier is ambiguous.
2. Run `archive.status` to check local evidence freshness.
3. Run `market.research` with `persist=true` when evidence is stale or missing.
4. Run `market.explain_move` if price movement is central to the question.
5. Run `wallet.whales` when whale flow is relevant.
6. Cite structured `evidence_sources`, `quality_flags`, and `recommended_actions`.

## Educated Guess / Winner Read

When a user asks for a fast opinion, do not overbuild a report. Pull the minimum
structured evidence needed to make an explicit, caveated call.

MCP sequence for a three-way sports market:

```json
{"tool":"market.search","args":{"query":"Mexico England game","limit":10}}
{"tool":"market.compare","args":{"markets":["<mex-slug>","<draw-slug>","<eng-slug>"],"hours":24}}
{"tool":"wallet.whales","args":{"min_notional":50000,"hours":24,"limit":10}}
```

Optional deeper checks:

```json
{"tool":"analytics.thesis","args":{"market":"<top-outcome-slug>"}}
{"tool":"market.explain_move","args":{"market":"<top-outcome-slug>","hours":24}}
```

Synthesis template:

1. State the pick first.
2. Show market-implied probability, recent move, and whale notional separately.
3. Mention whether whales are buying YES, buying NO, or split across outcomes.
4. Include one caveat from `quality_flags`, `errors`, or thin archive/history.
5. Label confidence; for near three-way splits, default to medium-low unless one
   signal is clearly dominant.

## Natural-Language Answer Path

Use `agent.answer` when the user wants a concise answer and does not need raw
intermediate data:

```bash
printf '{"tool":"agent.answer","args":{"query":"3 biggest whale wagers last 48 hours","hours":48,"limit":3,"min_notional":10000}}\n' | polyterm agent jsonl-server
```

Read the returned confidence, caveats, and tool trace. If the answer path reports
limited scan coverage or Data API errors, fall back to the underlying tools and
say exactly what failed.

## Caveats

PolyTerm data is public and can be incomplete. CLOB order books may be
unavailable for some token IDs. Data API wallet and trade surfaces can change.
Archive freshness only describes the local SQLite archive. None of these tools
is a trading signal by itself.
