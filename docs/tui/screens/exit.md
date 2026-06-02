# Exit Strategy Planner

> Plan profit targets and stop losses for your positions.

## Overview

The Exit Strategy Planner helps you define when to take profits or cut losses on market positions. You can create new exit plans with target prices or review previously saved plans. This screen provides a structured approach to trade management rather than making ad-hoc exit decisions.

## Access

- **Menu shortcut**: `ex` or `exitplan`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A menu with two options:

1. **Plan exit for a position** -- launches the interactive exit planner where you set profit targets and stop-loss levels
2. **View saved exit plans** -- lists previously created exit strategies

## Navigation / Keyboard Shortcuts

- `1` -- Plan a new exit strategy
- `2` -- View saved exit plans
- `b` -- Back to main menu

## CLI Command

```bash
# Interactive exit planning
polyterm exit --interactive

# List saved exit plans
polyterm exit --list
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for saved exit plans
- Gamma API for current market prices

## Related Screens

- [Fees](../screens/fees.md) -- understand costs affecting exit targets
- [Hot Markets](../screens/hot.md) -- identify markets with momentum for exit timing

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm the linked source file still exists and the module name has not changed.
- Update command examples, TUI shortcuts, and option names when Click or controller routing changes.
- Keep data-source notes current with the active Polymarket API contracts.
- Prefer concrete endpoint names, identifier types, and output fields over broad marketing language.
- Run `./test_all_commands.sh` when a CLI command or shortcut is affected.
- Run `.venv/bin/python scripts/validate_docs.py` before committing documentation changes.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Examples should be copy-pasteable from the repository root unless stated otherwise.
- Pages for view-only workflows should say so when wallet or trading context is involved.
- Pages that depend on live market data should name Gamma, Data API, or CLOB as the source.
- Alias pages should point to the canonical page and explain why the alias exists.
- New modules should have a dedicated page rather than relying only on the index.
