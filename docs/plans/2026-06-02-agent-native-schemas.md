# Agent-Native Schemas Implementation Plan

> **For Hermes:** Execute directly with strict TDD. Lobo disabled Kanban routing for this environment.

**Goal:** Make PolyTerm easier for any agent to consume by returning explicit machine-readable input/output schemas for every registered agent tool.

**Architecture:** Keep the existing stable response envelope, but enrich `polyterm agent schemas` with per-tool input schemas, envelope output schemas, safety metadata, and command/description metadata from the registry. This gives external agents enough structure to validate arguments, understand side effects, and reason about outputs without reading source code.

**Tech Stack:** Python, pytest, existing PolyTerm agent registry/contracts.

---

### Task 1: Add failing schema tests

**Objective:** Prove `schema_for_tool()` exposes actionable agent metadata, not only a generic envelope.

**Files:**
- Create: `tests/test_agent_schemas.py`
- Modify: none

**Checks:**
- `wallet.whales` schema has `tool`, `description`, `safety`, `input_schema`, and `output_schema`.
- `input_schema.properties` includes `min_notional`, `hours`, and `limit` with JSON Schema primitive types.
- Required args are inferred from command argument tokens, while optional args remain optional.
- Safety metadata mirrors registry flags.
- Unknown tools still raise `KeyError`.

### Task 2: Implement registry-driven schema generation

**Objective:** Enrich `polyterm.agent.schemas` without changing tool handlers.

**Files:**
- Modify: `polyterm/agent/schemas.py`

**Implementation:**
- Add an argument type mapper from registry arg strings (`string`, `integer`, `number`, `boolean`) to JSON Schema types.
- Infer required args by parsing `{arg_name}` tokens in `AgentTool.command`.
- Return a top-level schema packet containing:
  - `tool`
  - `description`
  - `command`
  - `schema_path`
  - `safety`
  - `input_schema`
  - `output_schema`
- Keep the base envelope schema shape intact under `output_schema`.

### Task 3: Verify CLI and MCP contract

**Objective:** Confirm the richer schema is visible to agents through CLI and does not break MCP manifest/tool tests.

**Commands:**
- `pytest tests/test_agent_schemas.py -q`
- `pytest tests/test_agent_mcp.py tests/test_agent_schemas.py -q`
- `polyterm agent schemas wallet.whales --format json`

### Task 4: Update documentation

**Objective:** Document that agent schemas now include input/output/safety metadata.

**Files:**
- Modify relevant agent docs if present.
- If no dedicated doc exists, update `README.md` agent-native section.

### Task 5: Full verification and ship

**Commands:**
- `pytest -q`
- `python scripts/validate_docs.py`
- `git status --short --branch`
- Commit and push to `main`.
