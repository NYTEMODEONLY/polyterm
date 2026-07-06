# Agent Mode

PolyTerm exposes an agent-safe tool surface for Hermes Agent, OpenClaw, Codex, and other automation systems that need Polymarket intelligence without scraping terminal tables.

## What Agents Can Do

Agents can:

- Discover PolyTerm tools with `polyterm agent manifest --format json`.
- Fetch JSON Schemas with `polyterm agent schemas --format json`.
- Diagnose install and MCP health with `polyterm agent doctor --format json`.
- Use the real MCP stdio server with `polyterm agent mcp-server`.
- Use the legacy JSON-lines adapter with `polyterm agent jsonl-server`.
- Search and resolve markets.
- Inspect CLOB order books and price history.
- Generate market-level trade theses.
- Inspect wallets and wallet-level whale activity.
- Export local archive manifests.
- Create local alert rules when policy allows local-state mutation.

Agents cannot:

- Place trades.
- Handle private keys.
- Approve contracts.
- Bridge funds.
- Mutate external Polymarket state.

## Stable Envelope

Agent tools return this envelope:

```json
{
  "schema_version": "2026-06-25",
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "generated_at": "2026-06-25T00:00:00Z"
  }
}
```

Failures use the same shape with `success: false` and an error string.

## Tool Discovery

```bash
polyterm agent manifest --format json
```

The manifest includes:

- `name`
- `description`
- `command`
- `args`
- `schema`
- `read_only`
- `mutates_local_state`
- `requires_confirmation`
- `may_prompt`
- `long_running`
- `adapter_available`
- `live_data`
- `examples`

The manifest also includes `cli_commands`, a complete 88-command CLI catalog for agents that need the broader PolyTerm suite beyond stable adapter tools.

The manifest's `adapters` block declares the standard MCP command, the JSON-lines fallback command, required optional extras, transports, and adapter tool counts.

Agents should reject or require explicit approval for tools where `mutates_local_state` is `true`. Long-running tools should be run with finite schedules or cancellation support.

## Hermes Agent Workflow

```bash
pip install -e ".[mcp]"
polyterm agent manifest --format json
polyterm agent catalog --format json
polyterm agent mcp-server
```

The standard MCP server exposes the same 27 tool names as the manifest, including `agent.answer`, `market.top`, `wallet.whale_trades`, `trader.leaderboard`, `market.flips`, and `market.movers`. It uses the optional MCP SDK, so fresh environments should install the `mcp` extra before launching it.

JSON-lines fallback:

```bash
printf '{"tool":"market.top","args":{"limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"agent.answer","args":{"query":"top 3 whale wagers last 48 hours","hours":48,"limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"wallet.whale_trades","args":{"limit":5,"hours":24}}\n' | polyterm agent jsonl-server
printf '{"tool":"trader.leaderboard","args":{"limit":3,"hours":72,"min_win_rate":0.8}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.flips","args":{"limit":3,"hours":72,"min_volume":500,"rank_by":"largest_crossing_move"}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.movers","args":{"limit":3,"hours":48}}\n' | polyterm agent jsonl-server
polyterm thesis -m "bitcoin" --format json
polyterm wallets --analyze 0xabc... --refresh --format json
polyterm arbitrage --venues polymarket,kalshi --query bitcoin --format json
```

Configure Hermes Agent or another MCP client with the real stdio server:

```yaml
mcp_servers:
  polyterm:
    command: "polyterm"
    args: ["agent", "mcp-server"]
    timeout: 120
    connect_timeout: 60
```

After restarting the client, tools are exposed through MCP as `agent.manifest`, `agent.schemas`, `agent.doctor`, `agent.answer`, `market.search`, `market.resolve`, `market.top`, `market.orderbook`, `market.price_history`, `market.movers`, `market.flips`, `market.research`, `market.explain_move`, `market.compare`, `scan.opportunities`, `archive.search`, `archive.status`, `archive.manifest`, `analytics.arbitrage`, `analytics.risk`, `analytics.thesis`, `wallet.inspect`, `wallet.whales`, `wallet.whale_trades`, `wallet.smart_money`, `trader.leaderboard`, `alerts.create_price_rule`, and `watch.scheduled_scan`.

Hermes Agent exposes those MCP names through its own tool prefix, for example `mcp_polyterm_agent_answer`, `mcp_polyterm_market_search`, `mcp_polyterm_market_compare`, `mcp_polyterm_wallet_whales`, and `mcp_polyterm_wallet_whale_trades`.

```bash
polyterm agent mcp-server
```

Recommended sequence:

1. Use `agent.answer` for broad natural-language Polymarket questions when a concise answer with confidence, caveats, and tool trace is enough.
2. Use `market.research` for a complete one-call brief.
3. Use `market.flips` when the user asks which markets flipped, crossed 50%, or moved above/below the YES majority line in a recent window.
4. Use `market.movers` when the user asks for broader spikes or large available Gamma price changes, not necessarily confirmed 50% crossings.
5. Use `market.explain_move` when the user asks why a specific YES price moved recently; it uses explicit CLOB `startTs` and `endTs` bounds for the requested window.
6. Use `market.compare` when the user asks which of several related markets looks divergent or mispriced.
7. Use `scan.opportunities` to find fresh movers, stale archive coverage, and markets that need research.
8. Use `wallet.whale_trades` for deterministic top-trade rankings; always report rows/pages scanned and Data API caveats.
9. Use `wallet.whales` for recent wallet-level whale flow; filter returned trades by the relevant market slugs before drawing conclusions.
10. Use `wallet.smart_money` for the local high win-rate wallet leaderboard; refresh evidence first when recency matters.
11. Resolve or search for a market when identifiers are ambiguous.
12. Generate a lower-level thesis when you need raw thesis internals.
13. Check cross-venue spreads.
14. Collect snapshots if the market needs observation over time.
15. Create local alert rules only after policy approval.

For questions like "What are the top 3 markets that have flipped in the last 72 hours?", call `market.flips` first:

```json
{
  "tool": "market.flips",
  "args": {
    "hours": 72,
    "limit": 3,
    "min_volume": 500,
    "active_only": true,
    "rank_by": "largest_crossing_move"
  }
}
```

The tool scans active Gamma markets, pulls CLOB YES-token price history with explicit `startTs` and `endTs`, detects confirmed 50% crossings, and returns crossing timestamps, start/end prices, min/max price, current bid/ask/spread, volume, liquidity, thin-market flags, and provenance quality flags. Supported ranking modes are `largest_crossing_move`, `highest_24h_volume`, `highest_liquidity`, `freshest_cross`, and `near_50_after_flip`; `direction` accepts `both`, `above`, or `below`.

## OpenClaw Workflow

OpenClaw-style tools that need line-delimited JSON without a full MCP client can use the legacy JSON-lines adapter:

```bash
printf '{"method":"manifest"}\n' | polyterm agent jsonl-server
printf '{"tool":"agent.answer","args":{"query":"top 3 whale wagers last 48 hours","hours":48,"limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.search","args":{"query":"bitcoin","limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.research","args":{"market":"bitcoin"}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.explain_move","args":{"market":"bitcoin","hours":24}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.compare","args":{"markets":["bitcoin 100k","bitcoin 90k"],"hours":24}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.flips","args":{"hours":72,"limit":3,"min_volume":500}}\n' | polyterm agent jsonl-server
printf '{"tool":"agent.doctor","args":{"skip_network":true}}\n' | polyterm agent jsonl-server
printf '{"tool":"scan.opportunities","args":{"query":"bitcoin","limit":5,"min_volume":5000}}\n' | polyterm agent jsonl-server
printf '{"tool":"archive.search","args":{"query":"bitcoin","limit":5}}\n' | polyterm agent jsonl-server
printf '{"tool":"archive.status","args":{"query":"bitcoin","max_age_hours":24}}\n' | polyterm agent jsonl-server
printf '{"tool":"wallet.smart_money","args":{"min_win_rate":0.7,"min_trades":10,"limit":20}}\n' | polyterm agent jsonl-server
printf '{"tool":"analytics.thesis","args":{"market":"bitcoin"}}\n' | polyterm agent jsonl-server
```

The legacy JSON-lines adapter does not require an MCP Python dependency. The production MCP server is implemented with FastMCP and reuses the same grouped tool functions.

## Agentic Synthesis Protocol

For user questions that ask for a judgment call, educated guess, winner, value side, or whale read, agents should use PolyTerm as evidence and synthesize explicitly:

1. **Resolve/search** the market set first; never guess identifiers.
2. **Compare all related outcomes** with `market.compare` for multi-outcome markets such as sports moneylines.
3. **Inspect recent movement** with `market.explain_move` or `market.price_history` when timing matters.
4. **Pull whale evidence** with `wallet.whales` or `wallet.whale_trades`; report scan coverage and Data API errors.
5. **Use `analytics.thesis`** for lower-level risk, liquidity, and order-book context when the answer depends on conviction.
6. **Separate facts from derived judgment**: market probabilities, 24h moves, whale notional, and final opinion should be distinct.
7. **Caveat outages**: if Data API pages timeout or `whale_flow_unavailable` appears, say so and fall back to the evidence that actually returned.

The full operational playbook is in [Agentic Usage Guide](AGENTIC_USAGE.md).

## Safety Classes

| Class | Meaning | Examples |
|-------|---------|----------|
| Read-only | Reads APIs or local state only | `market.research`, `market.explain_move`, `scan.opportunities`, `archive.search`, `archive.status`, `analytics.thesis`, `market.search`, `wallet.inspect`, `wallet.smart_money` |
| Local mutation | Changes local SQLite state | `alerts.create_price_rule`, future notes/bookmark tools |
| Long-running | Foreground process that may need cancellation | `watch.scheduled_scan`, collection workflows |
| Prompting | Not suitable for unattended agents | Interactive table commands without JSON mode |

## Identifier Rules

Agents must not mix Polymarket identifier types:

- Gamma market IDs and Gamma slugs are used for discovery and metadata.
- CLOB condition IDs identify CLOB markets.
- CLOB token IDs identify YES/NO order book tokens.
- Data API wallet calls use wallet/proxy wallet addresses.

The `market.resolve` tool and `polyterm thesis --format json` include the identifiers they can infer.

## Verification

```bash
polyterm agent manifest --format json
polyterm agent schemas --format json
polyterm agent mcp-server
printf '{"tool":"market.search","args":{"query":"bitcoin","limit":1}}\n' | polyterm agent jsonl-server
```

Run these repo gates after changing agent workflows:

```bash
./test_all_commands.sh
.venv/bin/python scripts/validate_docs.py
```

## Related Agent Docs

- [Agent config examples](AGENT_CONFIG_EXAMPLES.md)
- [Agent cookbook](AGENT_COOKBOOK.md)
- [Agentic usage guide](AGENTIC_USAGE.md)
- [Full LLM reference](../llms-full.txt)
