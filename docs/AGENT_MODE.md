# Agent Mode

PolyTerm exposes an agent-safe tool surface for Hermes Agent, OpenClaw, Codex, and other automation systems that need Polymarket intelligence without scraping terminal tables.

## What Agents Can Do

Agents can:

- Discover PolyTerm tools with `polyterm agent manifest --format json`.
- Fetch JSON Schemas with `polyterm agent schemas --format json`.
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
  "schema_version": "2026-06-02",
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "generated_at": "2026-06-02T00:00:00Z"
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

Agents should reject or require explicit approval for tools where `mutates_local_state` is `true`. Long-running tools should be run with finite schedules or cancellation support.

## Hermes Agent Workflow

```bash
polyterm agent manifest --format json
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

After restarting the client, tools are exposed through MCP as `agent.manifest`, `agent.schemas`, `market.search`, `market.resolve`, `market.research`, `archive.search`, `analytics.arbitrage`, `analytics.thesis`, `wallet.inspect`, and `wallet.whales`.

```bash
polyterm agent mcp-server
```

Recommended sequence:

1. Use `market.research` for a complete one-call brief.
2. Resolve or search for a market when identifiers are ambiguous.
3. Generate a lower-level thesis when you need raw thesis internals.
4. Inspect wallet/whale activity if the thesis depends on smart money.
5. Check cross-venue spreads.
6. Collect snapshots if the market needs observation over time.
7. Create local alert rules only after policy approval.

## OpenClaw Workflow

OpenClaw-style tools that need line-delimited JSON without a full MCP client can use the legacy JSON-lines adapter:

```bash
printf '{"method":"manifest"}\n' | polyterm agent jsonl-server
printf '{"tool":"market.search","args":{"query":"bitcoin","limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.research","args":{"market":"bitcoin"}}\n' | polyterm agent jsonl-server
printf '{"tool":"archive.search","args":{"query":"bitcoin","limit":5}}\n' | polyterm agent jsonl-server
printf '{"tool":"analytics.thesis","args":{"market":"bitcoin"}}\n' | polyterm agent jsonl-server
```

The legacy JSON-lines adapter does not require an MCP Python dependency. The production MCP server is implemented with FastMCP and reuses the same grouped tool functions.

## Safety Classes

| Class | Meaning | Examples |
|-------|---------|----------|
| Read-only | Reads APIs or local state only | `market.research`, `archive.search`, `analytics.thesis`, `market.search`, `wallet.inspect` |
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
