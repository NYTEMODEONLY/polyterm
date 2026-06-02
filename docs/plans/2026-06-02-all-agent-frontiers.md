# PolyTerm Agent Frontiers Full Implementation Plan

> **For Hermes:** Execute directly with strict TDD. Lobo has disabled Kanban routing for this environment; Alice owns implementation, verification, commits, gateway restart, and MCP proof.

**Goal:** Fully implement the remaining agent-native frontiers so PolyTerm becomes the de facto Polymarket toolkit any agent can use for full utility, research, and tooling.

**Architecture:** Build from the already-shipped agent spine: `market.research`, `analytics.thesis`, `wallet.whales`, `agent.manifest`, and `agent.schemas`. Each frontier adds stable JSON outputs, docs, schemas, MCP exposure, tests, and runtime verification.

**Tech Stack:** Python, Click, FastMCP, SQLite, Polymarket Gamma/CLOB/Data APIs, pytest, docs validator.

---

## Phase Status

### Phase 1 — Agent-native foundation

Status: complete.

Already shipped:
- FastMCP server.
- `agent.manifest`.
- `agent.schemas`.
- rich tool schemas/safety metadata.
- live `wallet.whales` with public Data API and local cache.

### Phase 2 — Research-grade market workflows

Status: flagship complete; refinements remain.

Already shipped:
- `analytics.thesis`.
- cached whale-flow evidence.
- structured `evidence_sources`.
- flagship `market.research` CLI/MCP/JSONL/schema/docs.

Remaining Phase 2 refinements:
1. Add richer market move explanation.
2. Add source-weighted confidence.
3. Add compare/divergence tools.

### Phase 3 — Local evidence archive

Status: next active implementation phase.

Goal: research compounds over time.

Tasks:
1. Persist `market.research` outputs as local research-brief evidence.
2. Add archive status/search tool for stored briefs.
3. Add staleness metadata and latest-prior comparison.
4. Cache market snapshots, orderbooks, and price history.

### Phase 4 — Agent workflow tools

Status: pending after archive foundation.

Tools:
- `market.explain_move`.
- `market.compare`.
- `wallet.smart_money`.
- `scan.opportunities`.
- `scan.anomalies`.
- `archive.search`.

### Phase 5 — Distribution polish

Status: pending after workflow tools.

Tasks:
- `polyterm agent doctor`.
- `llms.txt` and `llms-full.txt` updates.
- MCP config examples for Hermes, Claude Desktop, Cursor, OpenClaw.
- agent cookbook docs.

---

## Active Slice: Phase 3A — Research Brief Archive

**Objective:** Every `market.research` run should optionally persist a stable local archive record so agents can inspect prior research, detect staleness, and compare future briefs.

### Acceptance Criteria

- `MarketResearchEngine.build(..., persist=True)` stores a local research brief.
- Default CLI/MCP behavior remains read-only/no external mutation; local persistence is explicit unless set by command flag.
- Archived record stores:
  - market query
  - market id/slug/question/condition id
  - generated timestamp
  - brief
  - quality flags
  - workflow
  - full research payload JSON
- Archive can return latest briefs filtered by market/query.
- CLI exposes archive search/status through existing `polyterm collect` or new archive agent tool if cleaner.
- MCP exposes read-only `archive.search` for agents.
- Agent schemas include archive tool metadata.
- Tests cover persistence, search, schema/manifest, CLI/MCP handler.

### Test Commands

```bash
pytest tests/test_market_research.py tests/test_research_archive.py -q
pytest tests/test_agent_mcp.py tests/test_agent_schemas.py -q
python scripts/validate_docs.py
polyterm research --market bitcoin --format json
polyterm agent manifest --format json
polyterm agent schemas archive.search --format json
```

### Shipping Commands

```bash
pytest -q
git status --short --branch
git add <changed files>
git commit -m "feat: archive market research briefs"
git push origin main
```

After push, restart Hermes gateway externally and verify MCP with a cron job.
