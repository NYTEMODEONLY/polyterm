# Phase 3B Archive Status and Freshness Implementation Plan

> **For Hermes:** Execute directly with strict TDD. Lobo has disabled Kanban routing for this environment.

**Goal:** Add an agent-native archive freshness/status layer so PolyTerm can report what local evidence exists for a market, whether it is stale, and what should be refreshed before research.

**Architecture:** Reuse PolyTerm's local SQLite archive tables (`market_snapshots`, `research_briefs`, cached trades/wallets) and add a small `ArchiveCollector.status()` API. Expose it through `polyterm archive status`, MCP `archive.status`, rich schemas, docs, and the manifest.

**Tech Stack:** Python, Click, SQLite, pytest, FastMCP/JSONL agent registry.

---

## Task 1: Inspect current archive primitives

**Files:**
- Read: `polyterm/core/archive.py`
- Read: `polyterm/db/database.py`
- Read: `polyterm/cli/commands/archive.py`
- Read: `polyterm/agent/mcp/tools/archive.py`

**Verification:** identify which local evidence types can be counted without new live API calls.

## Task 2: RED — archive status core tests

**Objective:** Define expected status output.

**Test file:** `tests/test_archive_status.py`

Expected contract:
- `ArchiveCollector.status(query="bitcoin", market_id="m1", max_age_hours=24)` returns:
  - `success: true`
  - `query`
  - `market_id`
  - `evidence_counts.research_briefs`
  - `evidence_counts.market_snapshots`
  - `freshness.research_briefs.status`
  - `freshness.market_snapshots.status`
  - `quality_flags` containing `archive_status`
  - `recommended_actions`

Run expected RED command:

```bash
pytest tests/test_archive_status.py -q
```

Expected: FAIL because `status` does not exist.

## Task 3: GREEN — implement status core

**Files:**
- Modify: `polyterm/core/archive.py`
- Modify if needed: `polyterm/db/database.py`

Implementation:
- Add read-only query helpers for research brief and snapshot recency.
- Compute age hours from latest timestamp.
- Status values:
  - `fresh` if latest <= `max_age_hours`
  - `stale` if latest exists but older
  - `missing` if no rows
- Recommended actions:
  - missing/stale research → run `market.research` with `persist=true`
  - missing/stale snapshots → run `polyterm collect` / future snapshot collector

Verify:

```bash
pytest tests/test_archive_status.py -q
```

## Task 4: Expose CLI and MCP

**Files:**
- Modify: `polyterm/cli/commands/archive.py`
- Modify: `polyterm/agent/mcp/tools/archive.py`
- Modify: `polyterm/agent/mcp/server.py`
- Modify: `polyterm/agent/mcp/fastmcp_server.py`
- Modify: `polyterm/agent/registry.py`
- Create: `docs/schemas/archive.status.schema.json`

Commands:

```bash
polyterm archive status --query bitcoin --format json
printf '{"tool":"archive.status","args":{"query":"bitcoin"}}\n' | polyterm agent jsonl-server
```

## Task 5: Docs and verification

**Files:**
- Modify: `docs/cli/archive.md`
- Modify: `docs/core/archive.md`
- Modify: `docs/AGENT_MODE.md`
- Modify: `docs/tool-manifest.json`
- Modify: `README.md`

Verify:

```bash
pytest tests/test_archive_status.py tests/test_agent_mcp.py tests/test_agent_schemas.py -q
python scripts/validate_docs.py
pytest -q
```

## Task 6: Ship

```bash
git status --short --branch
git add <changed files>
git commit -m "feat: add archive freshness status"
git push origin main
```

Restart Hermes gateway externally and verify MCP `archive.status`.
