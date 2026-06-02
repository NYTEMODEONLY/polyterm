# Scenario Analysis Screen

> Model what-if outcomes for your positions.

## Overview

The Scenario Analysis screen lets you explore hypothetical outcomes for your portfolio or a specific market. You can see how different resolution scenarios would affect your P&L, helping you plan exit strategies and understand downside risk before committing to positions.

## Access

- **Menu shortcut**: `sc` or `scenario`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A menu with two options:

1. **Analyze portfolio** -- runs scenario analysis across all your positions
2. **Analyze specific market** -- prompts for a market name and models outcomes for that market

## Navigation / Keyboard Shortcuts

- Enter `1` for portfolio analysis, `2` for a specific market
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Portfolio | `polyterm scenario --portfolio` |
| Specific market | `polyterm scenario --market <market>` |

## Data Sources

- Local SQLite database for portfolio positions
- Gamma API for current market data and pricing

## Related Screens

- [Risk Assessment Screen](../screens/risk_screen.md)
- [Exit Plan Screen](../screens/exit.md)

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
