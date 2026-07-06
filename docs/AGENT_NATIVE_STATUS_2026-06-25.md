# Agent-Native Status - June 25, 2026

## Buildout Update

After the initial inspection, PolyTerm's agent-native surface was expanded and validated:

- The manifest now exposes 27 adapter-callable tools, including `agent.answer`, `market.top`, `wallet.whale_trades`, `trader.leaderboard`, `market.flips`, and `market.movers` for common natural-language market questions.
- `polyterm agent catalog --format json` exposes the full 88-command CLI catalog for agents that need the broader PolyTerm suite.
- `docs/tool-manifest.json` and `docs/schemas/*.schema.json` are generated from the live registry/schema code.
- The JSON-lines adapter now has handlers for every manifest tool.
- `polyterm agent mcp-server` exposes the same 27 tools through a standard MCP/FastMCP protocol server when the optional `.[mcp]` extra is installed.
- `polyterm agent jsonl-server` exposes the same tools through a dependency-free JSON-lines adapter.
- `tests/test_agent` covers manifest/static parity, schema artifacts, handler coverage, mutation safety, and live-tool normalization.
- The Data API leaderboard helper now uses the current documented `/v1/leaderboard` endpoint.
- The command smoke suite now includes the eager `update` command and reports 88 commands.

Remaining limits:

- Some non-agent CLI JSON modes still emit command-specific payloads rather than the versioned agent envelope.
- `trader.leaderboard` computes win-rate evidence from recent closed positions and labels that provenance with `quality_flags`; the public leaderboard endpoint itself supports PNL/VOL ranking, not native win-rate ranking.

This report captures the current state of PolyTerm's agent-native work after a full repo inspection on June 25, 2026. It is intended as the first handoff document for Hermes, OpenClaw, Codex, or another agent receiving the repo.

## Inspection Scope

- Local checkout: `/Users/lobo/Desktop/Progress/BI2025/polyterm`
- Git state at inspection start: `main` aligned with `origin/main`
- Release commit inspected: `cd70b54` (`Release PolyTerm v0.10.0`)
- Version reported by runtime: `python -m polyterm, version 0.10.0`
- Review lanes: main repo inspection plus subagents for agent/MCP surface, CLI/TUI docs, API/core/db contracts, and packaging/onboarding

## Current Bottom Line

PolyTerm is agent-native for repo-handoff discovery and the core live Polymarket questions in scope.

The repo now has a dedicated `polyterm/agent` package, a manifest command, schema command, standard MCP server, JSON-lines adapter, checked-in static manifest and schema files, `llms.txt`, an agent docs page, 27 adapter-callable tools, 88 CLI commands in the catalog, broad tests, and a no-custody safety model.

Remaining hardening is mostly incremental: broader nested schemas for lower-priority payloads, more CLI JSON envelope consistency outside the agent adapter, and docs validation that compares option tables to live Click help.

## What Is Implemented

### Agent Discovery

- `polyterm agent manifest --format json` emits a dynamic manifest from `polyterm/agent/registry.py`.
- `polyterm agent schemas --format json` emits schemas from `polyterm/agent/schemas.py`.
- `docs/tool-manifest.json` and `docs/schemas/*.schema.json` are checked in for static discovery.
- `llms.txt` points agents to the main entry points, safe commands, identifier rules, and API bases.
- `README.md` and `docs/AGENT_MODE.md` explicitly tell agents to inspect repo docs or call the manifest before assuming command behavior.

### Agent Execution Surface

- `polyterm agent mcp-server` runs a standard MCP/FastMCP protocol server when installed with `pip install -e ".[mcp]"`.
- `polyterm agent jsonl-server` runs a JSON-lines stdio adapter with no MCP dependency.
- Both adapters currently handle all 26 manifest tools:
  - `agent.answer`
  - `market.top`
  - `market.search`
  - `market.resolve`
  - `market.orderbook`
  - `market.price_history`
  - `market.movers`
  - `market.flips`
  - `market.research`
  - `market.explain_move`
  - `market.compare`
  - `scan.opportunities`
  - `analytics.arbitrage`
  - `analytics.risk`
  - `analytics.thesis`
  - `archive.search`
  - `archive.status`
  - `archive.manifest`
  - `alerts.create_price_rule`
  - `watch.scheduled_scan`
  - `wallet.inspect`
  - `wallet.whales`
  - `wallet.whale_trades`
  - `wallet.smart_money`
  - `trader.leaderboard`
- Responses use a stable top-level envelope:
  - `schema_version`
  - `success`
  - `data`
  - `error`
  - `meta`

### Agent-Relevant Product Features

- Market search and lookup paths exist.
- CLOB order book and chart commands support JSON mode.
- Wallet inspection and wallet-level whale workflows exist.
- Trade thesis generation exists.
- Research archive collection and dataset manifest export exist.
- Local alert rule creation exists and is documented as local-state mutation.
- Scheduled watch mode exists and is documented as long-running.
- No agent workflow places trades, handles private keys, approves contracts, bridges funds, or mutates external Polymarket state.

### Documentation and Validation Foundation

- `docs/README.md` indexes CLI, TUI, API, core, db, and utility docs.
- `scripts/validate_docs.py` checks module-to-doc existence, broken links, and stub-like docs.
- `test_all_commands.sh` smokes lazy command help, version, config, fees JSON, and search JSON.
- Broad local test subsets pass in the current checkout according to subagent verification.

## Main Gaps From Initial Inspection

### P0: Manifest and Adapter Do Not Match

**Status after buildout: resolved.**

The dynamic manifest registers 12 tools, but `polyterm/agent/mcp/server.py` wires only 6 handlers.

Missing adapter handlers:

- `market.orderbook`
- `market.price_history`
- `analytics.risk`
- `archive.manifest`
- `alerts.create_price_rule`
- `watch.scheduled_scan`

Observed behavior: a JSON-lines request for `market.orderbook` returns `Unknown tool: market.orderbook` even though the manifest advertises the tool.

Resolution: the manifest now registers 27 adapter-callable tools and every manifest tool has a handler in `polyterm/agent/mcp/server.py`. The new live tools cover natural-language answers, top markets, whale trades, active traders with win-rate evidence, confirmed market flips, and market movers.

### P0: Schemas Are Envelope-Only

**Status after buildout: partially resolved.**

The checked-in schemas and generated schemas currently constrain only the top-level envelope. The `data` field can be any object, array, string, number, boolean, or null.

This means agents can reliably detect success/failure, but cannot validate:

- input arguments
- identifier types
- nested response fields
- quality flags
- local mutation side effects
- long-running behavior

Resolution: schema artifacts are now generated from `polyterm.agent.schemas` and include tool-specific object contracts for the highest-use live and identifier tools. Remaining work is to keep enriching lower-priority payload schemas with stricter nested field contracts.

### P0: Dedicated Agent Tests Are Missing

**Status after buildout: resolved.**

There is no `tests/test_agent` suite in the current tree. Existing tests cover API/core/db/CLI behavior broadly, but not the agent contract layer directly.

Required next tests:

- `tests/test_agent/test_manifest_contracts.py`
- `tests/test_agent/test_schema_contracts.py`
- `tests/test_agent/test_mcp_tools.py`
- `tests/test_agent/test_static_artifacts.py`

Implemented assertions include:

- every manifest schema path exists
- static manifest matches dynamic manifest
- every adapter-advertised tool has a handler
- every handler returns the envelope
- unknown tools return a failed envelope
- mutating tools are flagged and require explicit policy approval or dry-run semantics

### P1: Static Manifest Is Too Thin

**Status after buildout: resolved.**

`docs/AGENT_MODE.md` says manifest entries include command, args, and confirmation flags. The dynamic manifest includes those fields. `docs/tool-manifest.json` only includes name, schema path, and a subset of safety booleans.

Resolution: `docs/tool-manifest.json` is generated from `polyterm.agent.registry.get_manifest()` and includes tool metadata plus the full CLI command catalog.

### P1: Command Templates Need Cleanup

**Status after buildout: resolved for manifest tools.**

Some manifest command templates are not safe enough for agents to synthesize directly.

Known issues:

- `alerts.create_price_rule` describes args `above` and `below`, but its command template contains `{price}`.
- `watch.scheduled_scan` lists a `market` arg, but the command template omits `--market {market}`.
- Some command templates omit useful manifest args such as `limit`.
- `alerts.create_price_rule` mutates local state and is marked `requires_confirmation: false`; that may be acceptable for a trusted local policy, but it is not conservative for unattended agents.

Resolution: alert and watch templates were corrected, alert mutation now requires confirmation, and adapter availability is explicit in the manifest.

### P1: Initial "MCP" Surface Was JSON-Lines, Not Standard MCP

**Status after buildout: resolved.**

The original adapter was useful, but it was not a full MCP protocol server. It did not implement standard MCP initialize, list tools, or call tool semantics. It is now kept separately as `polyterm agent jsonl-server`.

Resolution: `polyterm agent mcp-server` now uses the optional MCP Python SDK/FastMCP wrapper and registers the same 27 tool names as the JSON-lines adapter. `polyterm agent jsonl-server` remains available as a dependency-free JSON-lines adapter.

### P1: CLI JSON Output Is Uneven

Many CLI commands support `--format json`, but most emit ad hoc dictionaries through `print_json`, not the versioned agent envelope. Current output contract tests cover only a small subset, mainly `whales` and `mywallet --positions`.

Required next step: expand output contract tests for every manifest-backed CLI command:

- `search`
- `lookup`
- `orderbook`
- `chart`
- `risk`
- `thesis`
- `alerts`
- `watch`
- `export --dataset`

### P1: Docs Validation Does Not Catch Option Drift

`scripts/validate_docs.py` is clean, but it only checks file existence, links, and stubs. It does not compare command option tables against live Click help.

Known option-table drift found during inspection:

- `docs/cli/alerts.md` omits rule-creation options such as `--add-rule`, `--market`, `--above`, `--below`, and `--dry-run`.
- `docs/cli/watch.md` omits or misstates scheduled-mode fields such as `--schedule`, `--runs`, `--format`, and `--notify`.
- `docs/cli/export.md` says `--market` is required and omits `--dataset`, while the live command supports dataset manifests.

Required next step: add a docs validator mode that compares documented option tables with `polyterm <command> --help` for at least agent-facing commands.

### P1: Command Smoke Suite Skips `update`

**Status after buildout: resolved.**

`test_all_commands.sh` iterates `LAZY_COMMANDS`, which currently contains 87 commands. The live CLI also registers the eager `update` command in `polyterm/cli/main.py`, so `polyterm --help` shows 88 commands.

Resolution: `test_all_commands.sh` now includes `update` and reports 88 commands.

### P2: Onboarding and Packaging Need Cleanup

Fresh-agent setup has a few avoidable traps:

- `README.md` and `CONTRIBUTING.md` mention `pip install -e ".[dev]"`, but `setup.py` has no `extras_require`.
- Build/publish docs mention build tools that are not present in `requirements.txt`.
- Local ignored artifacts are stale: runtime reports `0.10.0`, while editable metadata and old `dist/` artifacts can report older versions.
- `MANIFEST.in` does not explicitly include `docs/`, `llms.txt`, or schema artifacts for source distributions, even though those files matter for repo-level agent discovery.

Resolution: `setup.py` now defines `dev` and `mcp` extras, and `MANIFEST.in` includes `docs/`, `docs/schemas/`, `docs/tool-manifest.json`, and `llms.txt`. Stale ignored artifacts should still be cleaned before release.

### P2: API Setup Docs Still Mention Deprecated Subgraph Enrichment

`API_SETUP.md` correctly says The Graph subgraph was removed, but its fallback section still lists Subgraph enrichment. Default config also still includes the deprecated subgraph endpoint.

Required next step: update API setup docs and decide whether the config should retain the deprecated endpoint as a legacy value or remove it from defaults.

## Recommended Next Work Order

1. **CLI JSON hardening:** ensure more non-agent CLI JSON paths emit pure, documented, stable JSON.
2. **Docs validator upgrade:** compare command option docs to live Click help for agent-facing commands.
3. **Schema enrichment:** keep tightening lower-priority nested `data` schemas and argument schemas.
4. **Release hygiene:** clean ignored build artifacts before release and rerun package verification.

## Verification Performed

Main inspection commands:

```bash
git status --short --branch
.venv/bin/python -m polyterm --version
.venv/bin/python -m polyterm agent manifest --format json
.venv/bin/python -m polyterm agent mcp-server --help
printf '{"method":"manifest"}\n{"tool":"market.search","args":{"query":"bitcoin","limit":1}}\n{"tool":"market.orderbook","args":{"token_id":"1"}}\n' | .venv/bin/python -m polyterm agent jsonl-server
.venv/bin/python scripts/validate_docs.py
./test_all_commands.sh
```

Verification during the buildout reported:

- Agent tests: `17 passed`
- API/Data API plus agent tests: `54 passed`
- CLI inventory/lazy/output-contract subset: `89 passed`
- CI-style suite excluding `tests/test_live_data` and `tests/test_tui/test_integration.py`: `1064 passed`
- Live data suite: `23 passed`
- Docs validation: `0` errors, `0` warnings
- Command smoke: `88` registered commands expose help

## Current Status Labels

| Area | Status | Reason |
|------|--------|--------|
| Agent docs entry points | Ready | README, `docs/AGENT_MODE.md`, `llms.txt`, manifest command, schemas command, and catalog command exist. |
| JSON-lines adapter | Ready for declared tools | 26 of 26 manifest tools are callable through the adapter. |
| Standard MCP compatibility | Ready with optional extra | `polyterm agent mcp-server` registers the 26 manifest tools through FastMCP when `.[mcp]` is installed. |
| Tool schemas | Partially ready | High-use live and identifier tools now have object schemas; deeper payload schemas can still be tightened. |
| Safety model | Ready for current adapter | No-custody model, flags, confirmation requirement, and mutation tests exist. |
| CLI JSON support | Partially ready | Many commands support JSON, but output contracts are uneven and under-tested. |
| Docs index coverage | Mostly ready | Module/doc mapping is clean, but option-table drift is not validated. |
| Fresh agent onboarding | Mostly ready | Dev extra and manifest/schema package inclusion were added; stale ignored artifacts should still be cleaned before release. |

## Handoff Note For Agents

Start with:

```bash
.venv/bin/python -m polyterm agent manifest --format json
.venv/bin/python -m polyterm agent schemas --format json
.venv/bin/python -m polyterm agent catalog --format json
.venv/bin/python -m polyterm agent mcp-server --help
.venv/bin/python scripts/validate_docs.py
./test_all_commands.sh
```

Use `polyterm agent mcp-server` for standard MCP clients after installing `pip install -e ".[mcp]"`. Use `polyterm agent jsonl-server` for JSON-lines shell workflows. Use the manifest's `adapter_available` field to decide which tools are callable through the adapters.
