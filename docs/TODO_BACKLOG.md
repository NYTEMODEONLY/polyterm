# TODO Backlog

Actionable work items linked to [EXECUTION_ROADMAP.md](./EXECUTION_ROADMAP.md). This backlog reflects the June 2, 2026 next-five roadmap and supersedes the older March backlog.

## P0: Agent Tool Contracts + MCP-Ready Surface

### TODO-1: Add `polyterm/agent` contract package

**Roadmap:** Feature 1  
**Priority:** P0  
**Effort:** M  
**Files:**

- `polyterm/agent/__init__.py`
- `polyterm/agent/registry.py`
- `polyterm/agent/contracts.py`
- `polyterm/agent/schemas.py`
- `tests/test_agent/test_registry.py`
- `tests/test_agent/test_contracts.py`

**Acceptance criteria:**

- Tool registry lists public agent tools with name, description, args, output schema, safety flags, and command mapping.
- Contract helper emits `schema_version`, `success`, `data`, `error`, and `meta`.
- Schema helper can validate sample payloads for search, resolve, orderbook, wallet, arbitrage, risk, prediction, and thesis tools.

### TODO-2: Generate agent manifest, schemas, and `llms.txt`

**Roadmap:** Feature 1  
**Priority:** P0  
**Effort:** M  
**Files:**

- `polyterm/agent/registry.py`
- `polyterm/agent/schemas.py`
- `docs/tool-manifest.json`
- `docs/schemas/*.schema.json`
- `docs/AGENT_MODE.md`
- `llms.txt`
- `tests/test_agent/test_schema_artifacts.py`

**Acceptance criteria:**

- `polyterm agent manifest --format json` emits a stable manifest.
- Generated or checked-in schema artifacts validate cleanly.
- `docs/AGENT_MODE.md` includes Hermes/OpenClaw examples, safety flags, and non-interactive usage rules.
- `llms.txt` maps the main commands, API clients, identifier rules, and agent-safe entry points.

### TODO-3: Add MCP read-only adapter

**Roadmap:** Feature 1  
**Priority:** P0  
**Effort:** L  
**Files:**

- `polyterm/agent/mcp/server.py`
- `polyterm/agent/mcp/tools/market.py`
- `polyterm/agent/mcp/tools/wallet.py`
- `polyterm/agent/mcp/tools/analytics.py`
- `docs/AGENT_MODE.md`
- `tests/test_agent/test_mcp_tools.py`

**Acceptance criteria:**

- MCP server exposes read-only market search, market resolve, order book, price history, wallet inspect, arbitrage scan, risk assess, and trade thesis tools.
- Each tool returns the versioned contract envelope.
- Mutating local-state commands are excluded or explicitly marked unavailable.

### TODO-4: Stabilize CLI JSON behavior for agent-declared tools

**Roadmap:** Feature 1  
**Priority:** P0  
**Effort:** M  
**Files:**

- `polyterm/utils/json_output.py`
- `polyterm/cli/commands/search.py`
- `polyterm/cli/commands/lookup.py`
- `polyterm/cli/commands/orderbook.py`
- `polyterm/cli/commands/arbitrage.py`
- `polyterm/cli/commands/risk.py`
- `polyterm/cli/commands/predict.py`
- `tests/test_cli/test_json_contract_inventory.py`

**Acceptance criteria:**

- Every schema-declared command emits parseable JSON with no Rich preamble on stdout.
- JSON mode never triggers interactive prompts.
- README and docs no longer claim unsupported commands have `--format json`.

## P1: Wallet Intelligence + True Whale Pipeline

### TODO-5: Add Data API wallet intelligence methods

**Roadmap:** Feature 2  
**Priority:** P1  
**Effort:** M  
**Files:**

- `polyterm/api/data_api.py`
- `tests/test_api/test_data_api.py`
- `docs/api/data_api.md`

**Acceptance criteria:**

- Data API client supports current positions, trades, activity, holders/value if available, and leaderboard/profile endpoints if available.
- Pagination, empty responses, rate limits, and malformed responses are tested.
- Docs state exact endpoint contracts and identifier requirements.

### TODO-6: Build wallet intelligence core module

**Roadmap:** Feature 2  
**Priority:** P1  
**Effort:** L  
**Files:**

- `polyterm/core/wallet_intelligence.py`
- `tests/test_core/test_wallet_intelligence.py`
- `docs/core/wallet_intelligence.md`

**Acceptance criteria:**

- Computes wallet P&L summary, ROI, win rate, market concentration, category exposure, recent large moves, and consensus signals.
- Labels inferred fields and data-quality caveats.
- Keeps parsing logic separate from CLI/TUI rendering.

### TODO-7: Upgrade `whales`, `wallets`, `leaderboard`, and `follow`

**Roadmap:** Feature 2  
**Priority:** P1  
**Effort:** L  
**Files:**

- `polyterm/cli/commands/whales.py`
- `polyterm/cli/commands/wallets.py`
- `polyterm/cli/commands/leaderboard.py`
- `polyterm/cli/commands/follow.py`
- `docs/cli/whales.md`
- `docs/cli/wallets.md`
- `docs/cli/leaderboard.md`
- `docs/cli/follow.md`
- `tests/test_cli/test_whales.py`
- `tests/test_cli/test_wallets.py`
- `tests/test_cli/test_leaderboard.py`

**Acceptance criteria:**

- `polyterm whales --wallets --format json` returns wallet-level whale activity.
- `polyterm wallets --analyze <address> --refresh --format json` returns live Data API-backed wallet profile data.
- `polyterm leaderboard --source data-api --format json` does not use seeded pseudo-data.
- Followed wallets can include max exposure and filter metadata.

## P1: Trade Thesis + Explainable Market Intelligence

### TODO-8: Add `trade_thesis` core module

**Roadmap:** Feature 3  
**Priority:** P1  
**Effort:** L  
**Files:**

- `polyterm/core/trade_thesis.py`
- `tests/test_core/test_trade_thesis.py`
- `docs/core/trade_thesis.md`

**Acceptance criteria:**

- Composes market metadata, CLOB prices/history/orderbook, prediction signals, risk score, whale signals, wash-trade indicators, UMA risk, news, and arbitrage.
- Returns evidence, caveats, confidence, and next actions in a deterministic schema.
- Uses existing market identifier utilities instead of duplicating slug/token logic.

### TODO-9: Add `thesis` CLI command and optional TUI screen

**Roadmap:** Feature 3  
**Priority:** P1  
**Effort:** M  
**Files:**

- `polyterm/cli/commands/thesis.py`
- `polyterm/cli/lazy_group.py`
- `polyterm/tui/screens/thesis_screen.py` (if TUI included)
- `docs/cli/thesis.md`
- `docs/tui/screens/thesis_screen.md` (if TUI included)
- `tests/test_cli/test_thesis.py`
- `tests/test_tui/test_screens.py` (if TUI included)

**Acceptance criteria:**

- `polyterm thesis -m <slug-or-url> --format json` returns a stable market-level thesis.
- `polyterm thesis -m <market> --brief` fits in one terminal screen.
- Agent manifest marks thesis as read-only and non-mutating.

## P2: Research Archive + Dataset Export Suite

### TODO-10: Add archive collection core and command

**Roadmap:** Feature 4  
**Priority:** P2  
**Effort:** L  
**Files:**

- `polyterm/core/archive.py`
- `polyterm/cli/commands/collect.py`
- `polyterm/db/database.py`
- `docs/core/archive.md`
- `docs/cli/collect.md`
- `tests/test_core/test_archive.py`
- `tests/test_cli/test_collect.py`

**Acceptance criteria:**

- `polyterm collect --market <slug> --interval 30s --duration 10m` records snapshots with run metadata.
- Archive rows include quality flags for API fallback, stale data, missing token IDs, rate-limit backoff, and partial runs.
- Collection can run in foreground and exits cleanly on Ctrl+C.

### TODO-11: Expand exports to dataset bundles

**Roadmap:** Feature 4  
**Priority:** P2  
**Effort:** M  
**Files:**

- `polyterm/cli/commands/export_cmd.py`
- `polyterm/core/archive.py`
- `docs/cli/export.md`
- `tests/test_cli/test_export.py`

**Acceptance criteria:**

- `polyterm export --dataset latest --format json` returns a dataset envelope.
- `polyterm export --dataset latest --format csv` exports multiple tables with stable column names.
- Optional XLSX export fails gracefully when optional dependency is unavailable.

## P2: Alert Automation + Cross-Venue Hedge Monitor

### TODO-12: Add unified alert engine

**Roadmap:** Feature 5  
**Priority:** P2  
**Effort:** L  
**Files:**

- `polyterm/core/alert_engine.py`
- `polyterm/cli/commands/alerts.py`
- `polyterm/cli/commands/watch.py`
- `docs/core/alerts.md`
- `docs/cli/alerts.md`
- `docs/cli/watch.md`
- `tests/test_core/test_alerts.py`
- `tests/test_cli/test_alerts.py`
- `tests/test_cli/test_watch.py`

**Acceptance criteria:**

- Alert rules support price breaks, whale trades, volume anomalies, new markets, resolution changes, and risk changes.
- Rule creation is local-state mutation and is marked as such in docs and manifests.
- `polyterm watch --schedule 15m --notify telegram --format json` runs without prompts.

### TODO-13: Add cross-venue hedge monitor

**Roadmap:** Feature 5  
**Priority:** P2  
**Effort:** L  
**Files:**

- `polyterm/core/cross_venue.py`
- `polyterm/api/kalshi.py`
- `polyterm/cli/commands/arbitrage.py`
- `docs/core/arbitrage.md`
- `docs/cli/arbitrage.md`
- `tests/test_core/test_arbitrage.py`
- `tests/test_cli/test_arbitrage.py`

**Acceptance criteria:**

- `polyterm arbitrage --venues polymarket,kalshi --format json` reports matched markets, match confidence, fee-adjusted spread, and stale-data risk.
- False-match risk is visible in table and JSON output.
- Missing venue credentials or unavailable venue APIs degrade gracefully.

## Shared Verification

Run these before finalizing substantial roadmap implementation work:

```bash
./test_all_commands.sh
.venv/bin/python scripts/validate_docs.py
```

Also run focused tests for touched modules, commands, and docs-sensitive changes.
