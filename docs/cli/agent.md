# Agent

> Agent manifests, schemas, standard MCP tooling, and JSON-lines stdio tooling for PolyTerm.

## Overview

`polyterm agent` exposes the command and schema surface that external agents use to call PolyTerm safely. The command is intentionally separate from market analysis commands so Hermes Agent, OpenClaw, Codex, and other agent runtimes can discover tools before they call them. It focuses on stable metadata, JSON Schemas, safety flags, a real FastMCP stdio server, and a lightweight legacy JSON-lines adapter.

The command does not execute trades or hold private keys. It exposes no-custody market intelligence, wallet inspection, archive metadata, and local alert-rule workflows with explicit mutation flags.

## Usage

### CLI

```bash
polyterm agent manifest --format json
polyterm agent schemas --format json
polyterm agent schemas analytics.thesis --format json
polyterm agent doctor --format json
polyterm agent mcp-server
polyterm agent jsonl-server
polyterm agent examples
```

### TUI

There is no TUI screen for agent setup. Agent workflows are intended for automation and stdio use. The TUI can still use the same underlying features through market, wallet, alert, and thesis commands.

## Options / Parameters

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `manifest` | command | - | Print the full tool manifest in a stable JSON envelope. |
| `schemas` | command | - | Print all schemas or a single tool schema. |
| `doctor` | command | - | Diagnose schema files, manifest sync, MCP boot, API connectivity, SQLite archive health, and Hermes config. |
| `mcp-server` | command | - | Run the real FastMCP stdio server for MCP clients. |
| `jsonl-server` | command | - | Run the legacy JSON-lines stdio adapter for simple pipe-based integrations. |
| `examples` | command | - | Print example JSON-lines requests. |
| `--skip-network` | flag | `false` | Skip Data API and CLOB connectivity checks in doctor mode. |
| `--format` | choice | `json` | Agent output format. Currently JSON only. |

## Examples

```bash
# Discover all agent-safe tools
polyterm agent manifest --format json

# Get schemas for every tool
polyterm agent schemas --format json

# Get one schema
polyterm agent schemas wallet.inspect --format json

# Diagnose the local agent/MCP installation
polyterm agent doctor --skip-network --format json

# Run the real MCP stdio server
polyterm agent mcp-server

# Legacy JSON-lines request
printf '{"tool":"market.search","args":{"query":"bitcoin","limit":3}}\n' | polyterm agent jsonl-server
```

## How It Works

The command reads metadata from `polyterm.agent.registry`, wraps output through `polyterm.agent.contracts`, and prints responses with `utils.json_output`. The FastMCP server in `polyterm.agent.mcp.fastmcp_server` dispatches to the same small grouped tool modules under `polyterm/agent/mcp/tools` as the legacy JSON-lines adapter.

MCP clients can configure PolyTerm as a stdio server:

```yaml
mcp_servers:
  polyterm:
    command: "polyterm"
    args: ["agent", "mcp-server"]
    timeout: 120
    connect_timeout: 60
```

## Data Sources

- `polyterm.agent.registry` for command metadata and safety flags.
- `polyterm.agent.schemas` for JSON Schema generation.
- `polyterm.agent.mcp.protocol` for standard MCP protocol registration through FastMCP.
- `polyterm.agent.mcp.server` for JSON-lines request dispatch.
- Gamma, CLOB, Data API, and local SQLite through the grouped tool functions.

## Agent Safety

Every manifest row includes:

- `read_only`
- `mutates_local_state`
- `requires_confirmation`
- `may_prompt`
- `long_running`
- `adapter_available`
- `live_data`
- `examples`

Agent runtimes should refuse tools that mutate local state unless their policy explicitly allows local state changes. They should also treat `long_running` tools as foreground processes that may need interruption.

## Schema Contract

`polyterm agent schemas [tool] --format json` returns agent-usable schema packets. Each packet includes:

- `tool`: registry tool name such as `wallet.whales`
- `description`: human-readable purpose
- `command`: equivalent CLI command pattern
- `schema_path`: checked-in schema path for docs/reference
- `safety`: `read_only`, `mutates_local_state`, `requires_confirmation`, `may_prompt`, and `long_running`
- `input_schema`: JSON Schema object for tool arguments, including inferred required args from command argument tokens
- `output_schema`: JSON Schema for PolyTerm's stable response envelope

Example single-tool payload inside the standard envelope:

```json
{
  "tool": "wallet.whales",
  "input_schema": {
    "type": "object",
    "properties": {
      "min_notional": {"type": "number"},
      "hours": {"type": "integer"},
      "limit": {"type": "integer"}
    },
    "required": [],
    "additionalProperties": false
  }
}
```

## Output Contract

Agent command outputs use:

```json
{
  "schema_version": "2026-06-25",
  "success": true,
  "data": {},
  "error": null,
  "meta": {}
}
```

The same envelope is used for successful and failed responses. Failures set `success` to `false` and put the error text in `error`.

## Doctor Checks

`polyterm agent doctor` runs bounded diagnostics that are safe for automation.
It checks that registry schema files exist and parse, the runtime registry is
in sync with `docs/tool-manifest.json`, the local SQLite archive is readable,
the FastMCP server can be constructed, and the Hermes config snippet is
available in the output. Unless `--skip-network` is used, it also probes the
Polymarket Data API and CLOB sampling markets endpoint.

The command returns a summary status of `ok`, `warn`, or `error`. Network
connectivity failures are warnings because an offline environment can still
have a valid local installation.

## Verification

```bash
polyterm agent manifest --format json
polyterm agent schemas --format json
polyterm agent doctor --skip-network --format json
polyterm agent examples
printf '{"method":"manifest"}\n' | polyterm agent jsonl-server
```

Run `./test_all_commands.sh` and `.venv/bin/python scripts/validate_docs.py` after changes.

## Related Features

- [Agent Mode](../AGENT_MODE.md)
- [Trade Thesis](thesis.md)
- [Wallets](wallets.md)
- [Whales](whales.md)
- [Export](export.md)
