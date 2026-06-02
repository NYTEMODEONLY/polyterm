# Project Agent Rules

These instructions apply to all work in this repository.

## Architecture Rule: No Monoliths

- Do not introduce monolithic files, modules, or command handlers.
- Prefer small, focused modules with clear single responsibilities.
- Keep features easy to edit, add, remove, and test in isolation.
- Split large changes into composable units (API layer, core logic, CLI/TUI wiring, tests).
- Favor explicit interfaces between modules over tightly coupled cross-module logic.
- When extending functionality, add or modify the smallest relevant module instead of expanding a central "god" file.

## Change Quality Gate

Before finalizing substantial changes, verify:

- The code path can be understood without reading unrelated modules.
- A future contributor can replace/remove a feature without broad refactors.
- Tests are scoped to behavior of the touched module(s), not accidental implementation details.

## Documentation Rule

- Keep `docs/README.md` aligned with the command, TUI, API, core, database, and utility modules that exist in the repo.
- When adding or renaming a module under `polyterm/cli/commands`, `polyterm/tui/screens`, `polyterm/api`, `polyterm/core`, `polyterm/db`, or `polyterm/utils`, add or update the matching page under `docs/`.
- Do not leave generated placeholder docs in the published tree. Replace stubs with a clear overview, source path, data sources, verification notes, and related documentation links.
- For API-facing changes, document the current Polymarket endpoint contract and identifier requirements. Be explicit about Gamma market IDs, Gamma slugs, CLOB condition IDs, and CLOB token IDs.
- For CLI/TUI changes, document the exact command, shortcuts, options, output modes, and whether the workflow is view-only or can mutate local state.
- Run `./test_all_commands.sh`, `.venv/bin/python scripts/validate_docs.py`, and focused tests for touched modules before committing documentation-sensitive changes.
