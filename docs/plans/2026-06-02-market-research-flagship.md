# Market Research Flagship Implementation Plan

> **For Hermes:** Execute directly with strict TDD. Lobo disabled Kanban routing for this environment.

**Goal:** Add `market.research`, PolyTerm's flagship one-call agent research brief for a Polymarket market/query.

**Architecture:** Build a small `MarketResearchEngine` that composes the existing deterministic `TradeThesisEngine` with optional live whale prefetch and agent-focused synthesis fields. Expose it through CLI, legacy JSON-lines agent handler, FastMCP, registry, schemas, and docs.

**Tech Stack:** Python, Click, FastMCP, PolyTerm agent envelope, pytest.

---

## Contract

`market.research` returns a stable envelope whose `data` includes:

- `query`: original user query/identifier
- `market`: resolved market identifiers and title
- `brief`: executive summary, thesis direction/confidence, recommendation, key evidence, key risks, gaps, next actions
- `thesis`: underlying `TradeThesisEngine.build()` result
- `quality_flags`: flattened flags including `research_brief`, thesis flags, and live-whale prefetch flags
- `workflow`: ordered tool calls that were run or recommended

## CLI

```bash
polyterm research --market bitcoin --format json
polyterm research --market bitcoin --prefetch-whales --min-notional 100000 --hours 72 --limit 5 --format json
```

## Agent/MCP

Tool name: `market.research`

Arguments:

- `market: string` required
- `prefetch_whales: boolean` optional; default false
- `min_notional: number` optional; default 100000
- `hours: integer` optional; default 72
- `limit: integer` optional; default 5

## TDD Tasks

### Task 1: Core research engine

**Files:**
- Create: `polyterm/core/market_research.py`
- Create: `tests/test_market_research.py`

**Test first:** Verify `MarketResearchEngine.build("bitcoin")` returns query, market, brief, thesis, workflow, and flattened quality flags.

**Implementation:** Compose `TradeThesisEngine.build()` and derive `brief` from thesis evidence/risks/evidence_sources.

### Task 2: Optional live whale prefetch

**Files:**
- Modify: `polyterm/core/market_research.py`
- Test: `tests/test_market_research.py`

**Test first:** Verify `prefetch_whales=True` calls injected whale provider with min_notional/hours/limit, appends workflow entry, and reruns/enriches thesis after local cache has a chance to update.

**Implementation:** Accept an optional whale provider callable for tests; default to `WalletIntelligence.live_whales` with `DataAPIClient` in production.

### Task 3: CLI command

**Files:**
- Create: `polyterm/cli/commands/research.py`
- Modify: `polyterm/cli/lazy_group.py`
- Test: targeted CLI smoke / existing command inventory

**Test first:** Verify command inventory includes `research` and JSON CLI emits `success: true`.

**Implementation:** Add Click command with JSON/table output.

### Task 4: Agent tools

**Files:**
- Modify: `polyterm/agent/mcp/tools/market.py` or analytics module as appropriate
- Modify: `polyterm/agent/mcp/server.py`
- Modify: `polyterm/agent/mcp/fastmcp_server.py`
- Modify: `polyterm/agent/registry.py`
- Add: `docs/schemas/market.research.schema.json`
- Modify: `docs/tool-manifest.json`
- Test: `tests/test_agent_mcp.py`, `tests/test_agent_schemas.py`

**Test first:** Verify manifest and FastMCP list/call `market.research`.

**Implementation:** Wire handler returning PolyTerm envelope.

### Task 5: Docs and verification

**Files:**
- Create: `docs/cli/research.md`
- Create: `docs/core/market_research.md`
- Modify: `docs/AGENT_MODE.md`, `README.md`

**Verify:**

```bash
pytest tests/test_market_research.py tests/test_agent_mcp.py tests/test_agent_schemas.py -q
python scripts/validate_docs.py
pytest -q
polyterm research --market bitcoin --format json
```

Commit and push to `main`; restart Hermes gateway if MCP surface changes.
