# Report Screen

> Generate comprehensive trading reports.

## Overview

The Report screen lets you generate different types of summary reports for your trading activity. Reports range from daily market summaries to deep dives on specific markets, giving you a structured view of market conditions and your portfolio performance.

## Access

- **Menu shortcut**: `rp` or `report`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A menu with four report types:

1. **Daily Report** -- market summary for the day
2. **Weekly Report** -- performance review for the week
3. **Portfolio Report** -- overview of your positions
4. **Market Report** -- deep dive on a specific market (prompts for market name)

## Navigation / Keyboard Shortcuts

- Enter a number `1`-`4` to select a report type
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Daily report | `polyterm report -t daily` |
| Weekly report | `polyterm report -t weekly` |
| Portfolio report | `polyterm report -t portfolio` |
| Market report | `polyterm report -t market -m <market>` |

## Data Sources

- Gamma API for market data
- Local SQLite database for portfolio and historical data

## Related Screens

- [Analytics](../screens/analyze_screen.md)

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
