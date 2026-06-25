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

The standard MCP server exposes the same 25 tool names as the manifest, including `market.top`, `wallet.whale_trades`, `trader.leaderboard`, and `market.movers`. It uses the optional MCP SDK, so fresh environments should install the `mcp` extra before launching it.

JSON-lines fallback:

```bash
printf '{"tool":"market.top","args":{"limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"wallet.whale_trades","args":{"limit":5,"hours":24}}\n' | polyterm agent jsonl-server
printf '{"tool":"trader.leaderboard","args":{"limit":3,"hours":72,"min_win_rate":0.8}}\n' | polyterm agent jsonl-server
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

After restarting the client, tools are exposed through MCP as `agent.manifest`, `agent.schemas`, `agent.doctor`, `market.search`, `market.resolve`, `market.top`, `market.orderbook`, `market.price_history`, `market.movers`, `market.research`, `market.explain_move`, `market.compare`, `scan.opportunities`, `archive.search`, `archive.status`, `archive.manifest`, `analytics.arbitrage`, `analytics.risk`, `analytics.thesis`, `wallet.inspect`, `wallet.whales`, `wallet.whale_trades`, `wallet.smart_money`, `trader.leaderboard`, `alerts.create_price_rule`, and `watch.scheduled_scan`.

```bash
polyterm agent mcp-server
```

Recommended sequence:

1. Use `market.research` for a complete one-call brief.
2. Use `market.explain_move` when the user asks why a YES price moved recently.
3. Use `market.compare` when the user asks which of several related markets looks divergent or mispriced.
4. Use `scan.opportunities` to find fresh movers, stale archive coverage, and markets that need research.
5. Use `wallet.smart_money` for the local high win-rate wallet leaderboard; refresh evidence first when recency matters.
6. Resolve or search for a market when identifiers are ambiguous.
7. Generate a lower-level thesis when you need raw thesis internals.
8. Inspect wallet/whale activity if the thesis depends on smart money.
9. Check cross-venue spreads.
10. Collect snapshots if the market needs observation over time.
11. Create local alert rules only after policy approval.

## OpenClaw Workflow

OpenClaw-style tools that need line-delimited JSON without a full MCP client can use the legacy JSON-lines adapter:

```bash
printf '{"method":"manifest"}\n' | polyterm agent jsonl-server
printf '{"tool":"market.search","args":{"query":"bitcoin","limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.research","args":{"market":"bitcoin"}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.explain_move","args":{"market":"bitcoin","hours":24}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.compare","args":{"markets":["bitcoin 100k","bitcoin 90k"],"hours":24}}\n' | polyterm agent jsonl-server
printf '{"tool":"agent.doctor","args":{"skip_network":true}}\n' | polyterm agent jsonl-server
printf '{"tool":"scan.opportunities","args":{"query":"bitcoin","limit":5,"min_volume":5000}}\n' | polyterm agent jsonl-server
printf '{"tool":"archive.search","args":{"query":"bitcoin","limit":5}}\n' | polyterm agent jsonl-server
printf '{"tool":"archive.status","args":{"query":"bitcoin","max_age_hours":24}}\n' | polyterm agent jsonl-server
printf '{"tool":"wallet.smart_money","args":{"min_win_rate":0.7,"min_trades":10,"limit":20}}\n' | polyterm agent jsonl-server
printf '{"tool":"analytics.thesis","args":{"market":"bitcoin"}}\n' | polyterm agent jsonl-server
```

The legacy JSON-lines adapter does not require an MCP Python dependency. The production MCP server is implemented with FastMCP and reuses the same grouped tool functions.

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
- [Full LLM reference](../llms-full.txt)
