# Size Screen

> Calculate optimal bet sizes using Kelly Criterion.

## Overview

The Size screen launches the interactive position size calculator. It uses the Kelly Criterion to determine optimal bet sizing based on the user's bankroll, probability estimate, and current market price. It provides full Kelly, fractional Kelly, and fixed percentage alternatives.

## Access

- **Menu shortcut**: `sz`, `size`
- **Menu path**: Page 2 (Size)

## What It Shows

An introductory panel, then launches the interactive CLI which calculates:

- Edge and expected value per dollar
- Full Kelly recommended size
- Fractional Kelly sizes (quarter, half)
- Fixed percentage alternatives (1%, 2%, 5%)
- Outcome projections (profit if win, loss if lose)

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. Interaction is handled by the interactive CLI subprocess.

## CLI Command

```bash
polyterm size -i
```

## Data Sources

- User input (bankroll, probability estimate, market price)

## Related Screens

- [simulate_screen](../screens/simulate_screen.md) -- P&L calculator for trade scenarios
- [spread_screen](../screens/spread_screen.md) -- execution cost analysis

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
