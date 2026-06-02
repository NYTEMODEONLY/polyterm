# Portfolio Health Check

> Comprehensive portfolio health analysis with grades.

## Overview

The Health screen analyzes your tracked portfolio and provides a health score with grades. It evaluates diversification, risk exposure, position concentration, and other factors to give you an overall assessment of your portfolio's condition. Available as a quick check or a detailed deep-dive.

## Access

- **Menu shortcut**: `hp` or `health`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A menu with two analysis levels:

1. **Quick health check** -- summary health score and key metrics
2. **Detailed analysis** -- in-depth breakdown of all health factors

## Navigation / Keyboard Shortcuts

- `1` -- Quick health check
- `2` -- Detailed analysis
- `b` -- Back to main menu

## CLI Command

```bash
polyterm health              # Quick health check
polyterm health --detailed   # Detailed analysis
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for tracked positions
- Gamma API for current market data

## Related Screens

- [Exit Strategy](../screens/exit.md) -- plan exits for unhealthy positions
- [Fees](../screens/fees.md) -- understand cost drag on portfolio health

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
