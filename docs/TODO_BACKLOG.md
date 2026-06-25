# TODO Backlog

This backlog reflects the June 25, 2026 agent-native buildout. The older June 2 next-five roadmap remains useful product context, but the original Feature 1 TODOs are now complete.

## Completed In The Agent-Native Buildout

- Agent registry, stable envelope helpers, and generated JSON Schemas exist under `polyterm/agent`.
- `polyterm agent manifest --format json` emits 25 adapter-callable tools plus the 88-command CLI catalog.
- `polyterm agent catalog --format json` exposes the full CLI command inventory for repo-handoff agents.
- `docs/tool-manifest.json`, `docs/schemas/*.schema.json`, `docs/AGENT_MODE.md`, `docs/cli/agent.md`, and `llms.txt` are checked in for static discovery.
- `polyterm agent mcp-server` exposes the manifest tools through the optional standard MCP/FastMCP server.
- `polyterm agent jsonl-server` remains as a dependency-free JSON-lines adapter.
- Live agent tools cover top markets, whale trades, active traders with win-rate evidence, and market movers.
- Mutating local-state tools are flagged and require explicit confirmation.
- `tests/test_agent` covers manifest/static parity, adapter coverage, standard MCP registration, mutation safety, and live-tool normalization.

## P0: Keep Agent Contracts Current

### TODO-1: Tighten Lower-Priority Nested Schemas

**Priority:** P0
**Effort:** M
**Files:**

- `polyterm/agent/schemas.py`
- `docs/schemas/*.schema.json`
- `tests/test_agent/test_manifest_contracts.py`

**Acceptance criteria:**

- Every manifest tool has a specific nested `data` object schema, not only the shared envelope.
- Identifier fields distinguish Gamma market IDs, Gamma slugs, CLOB condition IDs, CLOB token IDs, and wallet addresses.
- Schema regeneration keeps `docs/tool-manifest.json` and `docs/schemas/*.schema.json` in sync with `polyterm.agent.registry`.

### TODO-2: Add Adapter Output Snapshot Tests

**Priority:** P0
**Effort:** M
**Files:**

- `tests/test_agent/test_mcp_tools.py`
- `tests/test_agent/test_mcp_protocol.py`
- `tests/fixtures/agent/`

**Acceptance criteria:**

- JSON-lines and standard MCP adapters return the same envelope shape for representative requests.
- Snapshots cover success and failure paths for `market.top`, `wallet.whale_trades`, `trader.leaderboard`, `market.movers`, and `alerts.create_price_rule`.
- Snapshot tests normalize timestamps and live API values so they remain deterministic.

## P1: Harden CLI JSON For Agents

### TODO-3: Expand CLI JSON Contract Coverage

**Priority:** P1
**Effort:** L
**Files:**

- `polyterm/cli/commands/search.py`
- `polyterm/cli/commands/lookup.py`
- `polyterm/cli/commands/orderbook.py`
- `polyterm/cli/commands/chart.py`
- `polyterm/cli/commands/risk.py`
- `polyterm/cli/commands/thesis.py`
- `tests/test_cli/test_output_contracts.py`

**Acceptance criteria:**

- Agent-facing commands with `--format json` emit parseable JSON with no Rich preamble on stdout.
- Commands do not prompt in JSON mode.
- Tests cover success, empty result, and API error output for each command.

### TODO-4: Decide Envelope Scope For Non-Agent CLI Commands

**Priority:** P1
**Effort:** M
**Files:**

- `polyterm/utils/json_output.py`
- `docs/utils/json_output.md`
- Command docs under `docs/cli/`

**Acceptance criteria:**

- Docs state which commands emit the versioned agent envelope and which emit command-specific JSON.
- Any migration to the agent envelope is documented as a compatibility change.
- Existing downstream command JSON consumers are not silently broken.

## P1: Improve Documentation Drift Detection

### TODO-5: Compare CLI Docs Against Live Click Help

**Priority:** P1
**Effort:** L
**Files:**

- `scripts/validate_docs.py`
- `docs/cli/*.md`
- `tests/test_cli/test_command_inventory.py`

**Acceptance criteria:**

- The docs validator can compare documented option tables against `polyterm <command> --help` for selected agent-facing commands.
- Drift is reported with the command name, missing option, and doc path.
- The first enforced set includes `agent`, `alerts`, `watch`, `export`, `leaderboard`, `wallets`, `whales`, `search`, `lookup`, `orderbook`, and `thesis`.

## P2: Keep Live Intelligence Transparent

### TODO-6: Strengthen Win-Rate Provenance

**Priority:** P2
**Effort:** M
**Files:**

- `polyterm/agent/mcp/tools/live.py`
- `polyterm/api/data_api.py`
- `docs/api/data_api.md`
- `docs/cli/leaderboard.md`

**Acceptance criteria:**

- `trader.leaderboard` continues to label win rate as closed-position-derived evidence.
- If Polymarket exposes a native win-rate endpoint later, the tool records the endpoint and switches provenance flags explicitly.
- Tests cover traders with no closed positions, losses, and mixed wins/losses.

### TODO-7: Add Better Market-Mover Windows When API Supports Them

**Priority:** P2
**Effort:** M
**Files:**

- `polyterm/agent/mcp/tools/live.py`
- `docs/AGENT_MODE.md`
- `docs/schemas/market.movers.schema.json`

**Acceptance criteria:**

- `market.movers` uses true 48-hour changes when available from an API source or local archive.
- Until then, output keeps `change_window_uses_available_gamma_change_fields` in `quality_flags`.
- Docs remain explicit about whether the requested window is exact or best-effort.

## Verification

Run these before committing agent or documentation changes:

```bash
./test_all_commands.sh
.venv/bin/python scripts/validate_docs.py
.venv/bin/python -m pytest tests/test_agent tests/test_api/test_data_api.py -q
```

For release or handoff changes, also run:

```bash
.venv/bin/python -m pytest tests --ignore=tests/test_live_data --ignore=tests/test_tui/test_integration.py --tb=short -q
.venv/bin/python -m pytest tests/test_live_data -q
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```
