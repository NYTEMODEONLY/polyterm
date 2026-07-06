# Agent Config Examples

These examples configure PolyTerm as a no-custody Polymarket intelligence tool.
They expose read-only market, wallet, archive, scan, and diagnostic tools, plus
local alert-rule creation when the client policy allows local-state mutation.

## Prerequisites

Install PolyTerm and verify the agent surface:

```bash
polyterm agent doctor --skip-network --format json
polyterm agent manifest --format json
polyterm agent schemas --format json
```

For live API checks, omit `--skip-network`:

```bash
polyterm agent doctor --format json
```

## Hermes MCP

```yaml
mcp_servers:
  polyterm:
    command: "polyterm"
    args: ["agent", "mcp-server"]
    timeout: 120
    connect_timeout: 60
```

After restarting Hermes, verify that `agent.doctor`, `agent.answer`, `market.research`,
`market.explain_move`, `market.compare`, `scan.opportunities`,
`wallet.whales`, `wallet.whale_trades`, and `wallet.smart_money` are listed.
Hermes normally exposes them with an `mcp_polyterm_` prefix, for example
`mcp_polyterm_agent_answer`, `mcp_polyterm_market_compare`, and
`mcp_polyterm_wallet_whale_trades`.

## Claude Desktop MCP

Add a server entry to the Claude Desktop MCP config file:

```json
{
  "mcpServers": {
    "polyterm": {
      "command": "polyterm",
      "args": ["agent", "mcp-server"]
    }
  }
}
```

Restart Claude Desktop after editing the config. If `polyterm` is installed in
a virtual environment, use the absolute path to the executable.

## Cursor MCP

Use the same stdio server shape in Cursor's MCP settings:

```json
{
  "mcpServers": {
    "polyterm": {
      "command": "polyterm",
      "args": ["agent", "mcp-server"]
    }
  }
}
```

If Cursor cannot find the command, run:

```bash
which polyterm
```

Then replace `"polyterm"` with that absolute path.

## OpenClaw / JSON-Lines Adapter

Runtimes that do not speak MCP can use the JSON-lines adapter:

```bash
polyterm agent jsonl-server
```

Example requests:

```bash
printf '{"method":"manifest"}\n' | polyterm agent jsonl-server
printf '{"tool":"agent.doctor","args":{"skip_network":true}}\n' | polyterm agent jsonl-server
printf '{"tool":"agent.answer","args":{"query":"top 3 whale wagers last 48 hours","hours":48,"limit":3}}\n' | polyterm agent jsonl-server
printf '{"tool":"market.research","args":{"market":"bitcoin","persist":true}}\n' | polyterm agent jsonl-server
printf '{"tool":"scan.opportunities","args":{"query":"crypto","limit":5}}\n' | polyterm agent jsonl-server
printf '{"tool":"wallet.whale_trades","args":{"hours":48,"limit":3,"min_notional":10000,"sample_size":3000}}\n' | polyterm agent jsonl-server
```

## OpenAI-Compatible Tool Wrappers

For agents that need a command wrapper instead of MCP, call the CLI with JSON
output and parse the stable envelope:

```bash
polyterm research --market "bitcoin" --persist --format json
polyterm explain-move --market "bitcoin" --hours 24 --format json
polyterm compare -m "bitcoin 100k" -m "bitcoin 90k" --format json
polyterm scan-opportunities --query crypto --limit 10 --format json
polyterm agent doctor --skip-network --format json
```

Tool wrappers should preserve these safety policies:

- Read-only tools may run without confirmation.
- `alerts.create_price_rule` mutates local SQLite and should require policy approval.
- `watch.scheduled_scan` may run longer than a one-shot command and should have a timeout.
- No PolyTerm command should be granted private keys or custody permissions.

## Verification Checklist

```bash
polyterm agent doctor --skip-network --format json
polyterm agent schemas scan.opportunities --format json
printf '{"tool":"agent.doctor","args":{"skip_network":true}}\n' | polyterm agent jsonl-server
```

For MCP clients, restart the client after config changes and confirm the
server lists PolyTerm's agent tools.
