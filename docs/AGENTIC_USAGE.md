# Agentic Usage Guide

PolyTerm is designed to be called by autonomous agents as a no-custody Polymarket intelligence layer. This guide is the operational playbook for Hermes Agent, OpenClaw, Codex, Claude Desktop, Cursor, and any runtime that needs structured market data without scraping terminal tables.

## Core Contract

Every agent-facing tool returns the same envelope:

```json
{
  "schema_version": "2026-06-25",
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "generated_at": "2026-06-25T00:00:00Z",
    "tool": "market.search"
  }
}
```

Agent rules:

1. Inspect `success` and `error` before trusting `data`.
2. Use `data.quality_flags`, `data.errors`, `rows_scanned`, `pages_scanned`, and `evidence_sources` as first-class caveats.
3. Prefer tool names and JSON schemas from `polyterm agent manifest --format json` and `polyterm agent schemas --format json` over hard-coded assumptions.
4. Treat `alerts.create_price_rule` as local-state mutation and require policy approval.
5. Treat `watch.scheduled_scan` as long-running; run it only with a timeout, bounded schedule, or external process supervision.
6. Never grant PolyTerm private keys. PolyTerm does not place trades, sign orders, approve contracts, bridge funds, or custody assets.

## Entry Points

| Runtime | Preferred entry point | Use when |
|---|---|---|
| Hermes Agent | `polyterm agent mcp-server` | Hermes can register MCP stdio servers and expose `mcp_polyterm_*` tools. |
| OpenClaw | `polyterm agent jsonl-server` | The runtime can write one JSON request per line and parse one envelope per line. |
| Claude Desktop / Cursor | `polyterm agent mcp-server` | The client supports MCP stdio config. |
| Shell wrappers | `polyterm ... --format json` | A simple command tool needs one-shot JSON output. |

## Hermes Agent Setup

Configure Hermes with the FastMCP stdio server:

```yaml
mcp_servers:
  polyterm:
    command: "polyterm"
    args: ["agent", "mcp-server"]
    timeout: 120
    connect_timeout: 60
```

Then restart Hermes or the Hermes gateway. Hermes exposes MCP tools with its own prefix, for example:

| PolyTerm tool | Hermes tool name |
|---|---|
| `agent.manifest` | `mcp_polyterm_agent_manifest` |
| `agent.schemas` | `mcp_polyterm_agent_schemas` |
| `agent.answer` | `mcp_polyterm_agent_answer` |
| `market.search` | `mcp_polyterm_market_search` |
| `market.resolve` | `mcp_polyterm_market_resolve` |
| `market.compare` | `mcp_polyterm_market_compare` |
| `market.research` | `mcp_polyterm_market_research` |
| `analytics.thesis` | `mcp_polyterm_analytics_thesis` |
| `wallet.whales` | `mcp_polyterm_wallet_whales` |
| `wallet.whale_trades` | `mcp_polyterm_wallet_whale_trades` |
| `wallet.smart_money` | `mcp_polyterm_wallet_smart_money` |

Hermes verification:

```bash
polyterm agent doctor --skip-network --format json
polyterm agent manifest --format json
polyterm agent schemas --format json
```

From Hermes itself, verify at least:

1. `mcp_polyterm_agent_manifest`
2. `mcp_polyterm_market_search` with a small query
3. `mcp_polyterm_wallet_whale_trades` with a bounded `sample_size`

## OpenClaw Setup

OpenClaw-style agents can use the dependency-free JSON-lines adapter:

```bash
polyterm agent jsonl-server
```

One request per line:

```bash
printf '{"method":"manifest"}\n' | polyterm agent jsonl-server
printf '{"tool":"market.search","args":{"query":"bitcoin","limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"agent.answer","args":{"query":"top 3 whale wagers in the last 48 hours","hours":48,"limit":3,"min_notional":10000}}\n' | polyterm agent jsonl-server
printf '{"tool":"wallet.whale_trades","args":{"hours":48,"limit":3,"min_notional":10000,"sample_size":3000}}\n' | polyterm agent jsonl-server
```

Recommended OpenClaw wrapper behavior:

1. Start the adapter as a subprocess.
2. Send exactly one JSON object per line.
3. Parse each line as a complete PolyTerm envelope.
4. On `success: false`, report `error` directly and choose a fallback tool.
5. Kill/restart the subprocess after protocol errors or timeouts.

## Agentic Query Protocol

Use this protocol for user questions that ask for an opinion, forecast, “educated guess,” market read, whale read, or live odds.

### 1. Resolve before reasoning

Do not guess market IDs or mix identifier types. If the user gives a title, URL, slug, Gamma ID, condition ID, or token ID, call:

```json
{"tool":"market.resolve","args":{"identifier":"<user input>"}}
```

If the user gives a fuzzy topic, call:

```json
{"tool":"market.search","args":{"query":"<topic>","limit":10}}
```

### 2. Pull the market state

For one market:

```json
{"tool":"market.research","args":{"market":"<slug-or-id>","hours":72,"limit":5,"persist":false}}
```

For related outcomes or multi-outcome sports markets:

```json
{"tool":"market.compare","args":{"markets":["<slug-a>","<slug-b>","<slug-c>"],"hours":24}}
```

### 3. Pull movement and order-book context when timing matters

```json
{"tool":"market.explain_move","args":{"market":"<slug-or-id>","hours":24}}
{"tool":"market.price_history","args":{"market":"<slug-or-id>","hours":24}}
```

### 4. Pull whale and smart-money evidence

Use live whale flow when recent large wagers matter:

```json
{"tool":"wallet.whales","args":{"min_notional":50000,"hours":24,"limit":10}}
```

Use deterministic top-trade ranking for “biggest whale wager” questions:

```json
{"tool":"wallet.whale_trades","args":{"min_notional":10000,"hours":48,"limit":5,"sample_size":3000}}
```

Use local smart-money evidence when the user asks about high win-rate wallets:

```json
{"tool":"wallet.smart_money","args":{"min_win_rate":0.7,"min_trades":10,"limit":20}}
```

### 5. Synthesize, do not overclaim

A good answer distinguishes:

- **Market-implied probability** from `outcomePrices`, `probability`, bid/ask, or last trade.
- **Recent movement** from price-history tools.
- **Whale flow** from live Data API rows or local cache.
- **Tool caveats** from `quality_flags`, Data API errors, limited scan windows, or stale local archive evidence.

When live Data API pages timeout, say so and fall back to market prices, comparison, thesis, and whatever whale rows were actually scanned. Do not invent missing whale flow.

## Common Workflows

### Current odds for a game

1. `market.search` for the game.
2. Identify the moneyline/outcome markets.
3. Read `outcomePrices`, `bestBid`, `bestAsk`, `lastTradePrice`, `volume`, and `liquidity`.
4. Convert probabilities only after using tool output; label derived odds as derived.

### “Who do you think wins?”

1. `market.compare` across every outcome in the market set.
2. `analytics.thesis` for each top outcome if a deeper read is needed.
3. `wallet.whales` with a realistic threshold for the sport/market liquidity.
4. Filter whale rows by the relevant slugs/outcomes.
5. Rank: market probability, 24h move, whale notional, liquidity, caveats.
6. Answer with a single pick plus confidence and the evidence stack.

### Biggest whale wagers

1. Start with `wallet.whale_trades`.
2. Report `rows_scanned`, `pages_scanned`, `errors`, and `quality_flags`.
3. If zero rows were scanned because the Data API timed out, retry with a lower `sample_size` or lower `min_notional`.
4. If still blocked, say live whale tape is unavailable and do not fabricate trades.

### Research-worthy opportunities

1. `scan.opportunities` for the topic or global market set.
2. `archive.status` for stale evidence.
3. `market.research` for the top candidate, optionally with `persist=true`.
4. `market.explain_move` if the opportunity depends on price action.

## Safety and Permission Model

| Tool class | Policy |
|---|---|
| Read-only live tools | Safe for autonomous use. Still cite caveats. |
| Local archive reads | Safe for autonomous use. Archive freshness may be stale. |
| Local archive writes / `persist=true` | Local mutation; allowed only if the agent policy permits research caching. |
| `alerts.create_price_rule` | Requires explicit policy approval or dry-run mode. |
| `watch.scheduled_scan` | Requires bounded runtime or external supervision. |
| Trading / custody | Not supported by PolyTerm. |

## Verification Checklist For Agents

Run after install, upgrade, or MCP restart:

```bash
polyterm agent doctor --skip-network --format json
polyterm agent manifest --format json
polyterm agent schemas --format json
printf '{"tool":"market.search","args":{"query":"bitcoin","limit":1}}\n' | polyterm agent jsonl-server
printf '{"tool":"agent.answer","args":{"query":"top active markets","limit":1}}\n' | polyterm agent jsonl-server
```

For repository changes, run:

```bash
./test_all_commands.sh
.venv/bin/python scripts/validate_docs.py
```
