# Execution Roadmap

**Last updated:** 2026-06-02  
**Scope:** Next five implementation tracks for PolyTerm after the June 1 API audit  
**Team model:** 1 engineer + focused subagents  
**Primary objective:** Make PolyTerm the best no-custody intelligence and data terminal for Polymarket traders, researchers, data collectors, whale watchers, and external agents such as Hermes Agent and OpenClaw.

This roadmap supersedes the March 2026 roadmap. Several earlier P0 items are already done or partially done: CLOB price history exists, lazy CLI loading exists, docs validation is clean, and `analyze` is registered. The remaining work should focus on features that users are actively asking for and gaps found in the current repo.

## Evidence Basis

- Repo audit: PolyTerm already has broad CLI/TUI coverage, CLOB price history, CLOB WebSocket order book support, local SQLite state, and current Gamma/CLOB/Data API documentation.
- Repo gaps: agent schemas/manifests are absent, JSON contracts are not stable enough, `whales` is still partly a volume-spike proxy, leaderboard/profile data is not real Data API-backed, and exports are too narrow.
- Public demand scan: current Polymarket users and tool directories emphasize alerts, wallet intelligence, copy-trade controls, cross-venue arbitrage, P&L reconciliation, and research-grade data archives.
- Current API contracts: global Polymarket read surfaces are Gamma, Data API, and CLOB; CLOB market data uses token IDs, user WebSocket uses condition IDs, and authenticated trading requires L1/L2 credentials.

Source references for product and API direction:

- [Polymarket API Reference](https://docs.polymarket.com/api-reference)
- [Polymarket market concepts and identifiers](https://docs.polymarket.com/concepts)
- [Polymarket market WebSocket channel](https://docs.polymarket.com/market-data/websocket/market-channel)
- [Polymarket agents repository](https://github.com/Polymarket/agents)
- [pm.wiki Polymarket tools overview](https://pm.wiki/learn/best-polymarket-tools)
- [Tagwise wallet analytics](https://tagwise.xyz/)
- [Polyloly wallet and alert tooling](https://polyloly.com/)

## Product Stance

PolyTerm should stay no-custody by default. Do not make private-key management, approvals, bridging, or authenticated order placement part of this five-feature roadmap. The durable advantage is pre-trade intelligence, risk explanation, wallet intelligence, data collection, and agent-safe automation.

If execution support is considered later, it should be a separate optional builder track with explicit credentials, builder attribution, slippage checks, heartbeat/cancel safety, and no silent mutation. That is not in scope for the next five.

## Next Five Features

| Rank | Feature | Primary User | Agent Priority | Why Now |
|------|---------|--------------|----------------|---------|
| 1 | Agent Tool Contracts + MCP-Ready Surface | Hermes/OpenClaw, researchers, automators | Critical | Agents need stable schemas, tool manifests, safety flags, and non-interactive commands before any higher-level automation is trustworthy. |
| 2 | Wallet Intelligence + True Whale Pipeline | Whale watchers, copy-traders, researchers | High | Current `whales` is not yet true wallet-level whale tracking; public demand is strongest around smart money, top wallets, and consensus moves. |
| 3 | Trade Thesis + Explainable Market Intelligence | Traders, researchers | High | PolyTerm has many signals, but users and agents need one market-level decision object with confidence, risk, evidence, and caveats. |
| 4 | Research Archive + Dataset Export Suite | Data collectors, researchers, agents | High | Researchers need repeatable snapshots, replay, quality flags, and exports beyond one market snapshot. |
| 5 | Alert Automation + Cross-Venue Hedge Monitor | Active traders, whale watchers | Medium-High | Users want fewer manual checks: whale moves, price breaks, volume anomalies, new markets, resolution changes, and cross-venue spreads. |

## Feature 1: Agent Tool Contracts + MCP-Ready Surface

**Goal:** Make PolyTerm easy and safe for Hermes Agent, OpenClaw, Codex, and other agents to call without scraping terminal text or guessing command behavior.

### Implementation Ownership

- `polyterm/agent/registry.py`: command/tool registry generated from `LAZY_COMMANDS`, enriched with hand-authored safety metadata.
- `polyterm/agent/contracts.py`: stable JSON envelope helpers with `schema_version`, `success`, `data`, `error`, and `meta`.
- `polyterm/agent/schemas.py`: JSON Schema generation and validation helpers.
- `polyterm/agent/mcp/server.py`: thin MCP adapter over stable read-only tools.
- `polyterm/agent/mcp/tools/market.py`: market lookup, search, order book, price history.
- `polyterm/agent/mcp/tools/wallet.py`: wallet positions, trades, profile, whale signals.
- `polyterm/agent/mcp/tools/analytics.py`: arbitrage, risk, prediction, trade thesis.
- `docs/AGENT_MODE.md`: agent usage, safety model, examples for Hermes/OpenClaw.
- `docs/tool-manifest.json`: generated tool manifest.
- `docs/schemas/*.schema.json`: generated or checked-in schemas for public agent tools.
- `llms.txt`: concise LLM-facing project map.

### Acceptance Criteria

- `polyterm agent manifest --format json` emits every public agent tool with name, description, args, output schema path, `read_only`, `mutates_local_state`, `requires_confirmation`, and `may_prompt`.
- Stable envelope is used by all agent tools: `schema_version`, `success`, `data`, `error`, `meta`.
- MCP server exposes at least 8 read-only tools: search markets, resolve market, get order book, get price history, scan arbitrage, assess risk, inspect wallet, and generate trade thesis.
- JSON-mode agent tools never print Rich preamble text to stdout.
- Prompting and local mutation are rejected unless the tool manifest explicitly allows them.
- Tests cover manifest generation, schema validation, and pure JSON output for every schema-declared tool.

### Verification

```bash
.venv/bin/python -m pytest tests/test_cli/test_output_contracts.py
.venv/bin/python -m pytest tests/test_agent
.venv/bin/python scripts/validate_docs.py
./test_all_commands.sh
```

## Feature 2: Wallet Intelligence + True Whale Pipeline

**Goal:** Turn wallet and whale tracking into a real smart-money product surface, not just market-level volume detection.

### Implementation Ownership

- `polyterm/api/data_api.py`: add Data API methods for leaderboard, holders, value, market positions, and paginated user trades if supported by current endpoints.
- `polyterm/core/wallet_intelligence.py`: wallet profile scoring, ROI/P&L metrics, win rate, market concentration, category exposure, and consensus-move detection.
- `polyterm/core/whale_tracker.py`: expose the richer wallet-level pipeline through CLI/TUI paths.
- `polyterm/cli/commands/whales.py`: add `--wallets`, `--market`, `--min-notional`, `--since`, and agent-safe JSON output.
- `polyterm/cli/commands/wallets.py`: add real profile refresh from Data API and ranking filters.
- `polyterm/cli/commands/leaderboard.py`: replace pseudo-random representative data with live Data API-backed data.
- `polyterm/cli/commands/follow.py`: add per-wallet max exposure, category filters, and read-only consensus alerts.
- `docs/cli/whales.md`, `docs/cli/wallets.md`, `docs/cli/leaderboard.md`, `docs/core/whale_tracker.md`: document source contracts and limitations.

### Acceptance Criteria

- `polyterm whales --wallets --format json` returns wallet addresses, not just high-volume markets.
- `polyterm wallets --analyze <address> --refresh --format json` returns positions, trades, P&L summary, concentration, category exposure, and recent large moves from Data API.
- `polyterm leaderboard --source data-api --format json` no longer uses seeded pseudo-trader data.
- `polyterm follow --list --format json` includes caps, filters, and consensus-tracking metadata.
- The docs are explicit about public trade direction limitations and any endpoint fields that are inferred.
- Tests mock Data API wallet/profile/leaderboard responses and cover empty, rate-limited, and malformed responses.

### Verification

```bash
.venv/bin/python -m pytest tests/test_api/test_data_api.py
.venv/bin/python -m pytest tests/test_core/test_whale_tracker.py
.venv/bin/python -m pytest tests/test_cli/test_whales.py tests/test_cli/test_wallets.py tests/test_cli/test_leaderboard.py
.venv/bin/python scripts/validate_docs.py
./test_all_commands.sh
```

## Feature 3: Trade Thesis + Explainable Market Intelligence

**Goal:** Give traders and agents a single market-level analysis object that explains what PolyTerm thinks, why it thinks it, and what data quality limits apply.

### Implementation Ownership

- `polyterm/core/trade_thesis.py`: compose market metadata, price history, order book, risk score, prediction signals, whale signals, wash-trade indicators, UMA/resolution risk, news, and arbitrage.
- `polyterm/cli/commands/thesis.py`: new command to avoid overloading the current portfolio-oriented `analyze`.
- `polyterm/cli/lazy_group.py`: register `thesis`.
- `polyterm/tui/screens/thesis_screen.py`: compact market thesis screen if TUI scope is included in the sprint.
- `docs/cli/thesis.md`, `docs/core/trade_thesis.md`, `docs/tui/screens/thesis_screen.md`: document command, shortcuts, output modes, and data sources.

### Acceptance Criteria

- `polyterm thesis -m <slug-or-url> --format json` returns a deterministic schema with market identifiers, current prices, liquidity, signal direction, confidence, top evidence, top risks, caveats, and next actions.
- `polyterm thesis -m <market> --brief` fits in one terminal screen.
- The command resolves Polymarket URLs, Gamma slugs, Gamma IDs, condition IDs, and CLOB token IDs through the existing market utility layer.
- Confidence and recommendations are explainable; no opaque “buy/sell” output without factors.
- Runtime target: under 5 seconds for one market with live APIs available.
- Agent manifest marks this as read-only and non-mutating.

### Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_trade_thesis.py
.venv/bin/python -m pytest tests/test_cli/test_thesis.py
.venv/bin/python scripts/validate_docs.py
./test_all_commands.sh
```

## Feature 4: Research Archive + Dataset Export Suite

**Goal:** Make PolyTerm valuable for data collectors and researchers who need reproducible market datasets, not just terminal views.

### Implementation Ownership

- `polyterm/core/archive.py`: scheduled collection of market snapshots, order book summaries, price history, wallet activity, alerts, and quality flags.
- `polyterm/db/database.py`: focused migrations for archive runs, dataset metadata, and export records.
- `polyterm/cli/commands/collect.py`: read-only live collection command with interval, duration, market filters, and stdout-safe status.
- `polyterm/cli/commands/export_cmd.py`: expand from single market snapshot to dataset exports for markets, positions, alerts, snapshots, trades, wallet profiles, and archive runs.
- `polyterm/core/replay.py` or existing replay path: replay archived datasets with timestamp filters.
- `docs/cli/collect.md`, `docs/cli/export.md`, `docs/core/archive.md`, `docs/db/database.md`: document storage, schemas, retention, and verification notes.

### Acceptance Criteria

- `polyterm collect --market <slug> --interval 30s --duration 10m` records a dataset with metadata and quality flags.
- `polyterm export --dataset latest --format csv` exports multiple tables with stable column names.
- `polyterm export --dataset latest --format json` returns a machine-readable dataset envelope.
- Optional XLSX export is behind an optional dependency and gracefully reports if unavailable.
- Archive quality flags note API fallback, stale data, missing token IDs, rate-limit backoff, and partial runs.
- Agents can request dataset manifests without reading SQLite directly.

### Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_archive.py
.venv/bin/python -m pytest tests/test_cli/test_export.py tests/test_cli/test_collect.py
.venv/bin/python -m pytest tests/test_db/test_database.py
.venv/bin/python scripts/validate_docs.py
./test_all_commands.sh
```

## Feature 5: Alert Automation + Cross-Venue Hedge Monitor

**Goal:** Reduce manual market checking for traders and whale watchers while expanding PolyTerm’s edge in arbitrage and hedging workflows.

### Implementation Ownership

- `polyterm/core/alert_engine.py`: unified rules for price breaks, whale trades, volume anomalies, new markets, resolution changes, risk changes, and cross-venue spreads.
- `polyterm/core/cross_venue.py`: market matching and hedge state for Polymarket, Kalshi, and future venue adapters.
- `polyterm/api/kalshi.py`: focused Kalshi read-only client if not already present.
- `polyterm/cli/commands/alerts.py`: rule creation, listing, testing, and export.
- `polyterm/cli/commands/watch.py`: scheduled foreground scans with notification delivery.
- `polyterm/cli/commands/arbitrage.py`: add `--venues` and hedge-monitor output.
- `docs/core/alerts.md`, `docs/cli/alerts.md`, `docs/cli/watch.md`, `docs/core/arbitrage.md`: document exact mutating local-state behavior and notification channels.

### Acceptance Criteria

- `polyterm alerts add price --market <slug> --above 0.70` creates a local rule with JSON confirmation.
- `polyterm watch --schedule 15m --notify telegram --format json` runs scheduled scans without interactive prompts.
- `polyterm arbitrage --venues polymarket,kalshi --format json` reports matched markets, confidence, fee-adjusted spread, and stale-data risk.
- Alert rules can be dry-run tested before saving.
- Notifications include source, timestamp, market identifiers, rule ID, and a reproducible command.
- Agent manifest clearly marks alert creation as local-state mutation and scheduled watch as long-running.

### Verification

```bash
.venv/bin/python -m pytest tests/test_core/test_alerts.py tests/test_core/test_arbitrage.py
.venv/bin/python -m pytest tests/test_cli/test_alerts.py tests/test_cli/test_watch.py
.venv/bin/python scripts/validate_docs.py
./test_all_commands.sh
```

## Implementation Sequence

### Sprint 1: Agent Foundation

Ship Feature 1 first. Every later feature should publish schemas and manifest entries as it lands. This prevents another round of ad hoc JSON payloads.

### Sprint 2: Wallet and Whale Intelligence

Ship Feature 2. This directly addresses high-demand whale watching and fixes the current `whales` command mismatch.

### Sprint 3: Trade Thesis

Ship Feature 3. Use the Feature 1 contract layer and Feature 2 wallet intelligence so the thesis output is agent-safe from day one.

### Sprint 4: Archive and Export

Ship Feature 4. This turns PolyTerm from a live terminal into a durable research instrument.

### Sprint 5: Alerts and Cross-Venue Monitor

Ship Feature 5. This builds on the archive, wallet, and thesis outputs to create automated monitoring.

## Quality Gate

Before any feature is considered complete:

- Update matching docs under `docs/cli`, `docs/core`, `docs/api`, `docs/db`, `docs/tui/screens`, or `docs/utils` when modules are added or renamed.
- Update `docs/README.md` when new commands, modules, or screens are added.
- Keep API-facing docs explicit about Gamma market IDs, Gamma slugs, CLOB condition IDs, and CLOB token IDs.
- Mark agent tools with read-only/mutating/prompting/long-running flags.
- Run:

```bash
./test_all_commands.sh
.venv/bin/python scripts/validate_docs.py
```

- Also run focused tests for every touched module and command.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| JSON contract churn | Breaks Hermes/OpenClaw integrations | Ship schemas and versioned envelopes first. |
| Public Data API field drift | Wallet intelligence regressions | Centralize Data API parsing and cover malformed/empty response tests. |
| Overclaiming whale/trade direction | Misleads users | Label inferred fields and quality flags in CLI, docs, and schemas. |
| Alert spam | Users ignore notifications | Add rule test mode, severity thresholds, cooldowns, and grouped digests. |
| Cross-venue false matches | Bad arbitrage decisions | Include match confidence, source links, and manual review flags. |
| Scope creep into execution | Custody/security risk | Keep roadmap read-only/no-custody; make execution a separate future track. |
