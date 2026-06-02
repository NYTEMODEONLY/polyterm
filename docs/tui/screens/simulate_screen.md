# Simulate Screen

> Calculate potential profit/loss before trading.

## Overview

The Simulate screen launches the interactive position simulator. It helps users understand potential outcomes of a trade including profit/loss at various exit prices, ROI calculations, and fee impact -- all without placing an actual trade.

## Access

- **Menu shortcut**: `sim`, `simulate`
- **Menu path**: Page 2 (Simulate)

## What It Shows

An introductory panel explaining the simulator's capabilities:

- How much you could win or lose
- Potential ROI
- Outcomes at different exit prices
- Fee impact on returns

Then launches the interactive CLI which prompts for trade parameters.

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. Interaction is handled by the interactive CLI subprocess.

## CLI Command

```bash
polyterm simulate -i
```

## Data Sources

- User input (entry price, position size, exit scenarios)
- CLOB V2 protocol fee estimates, using market schedules when available

## Related Screens

- [size_screen](../screens/size_screen.md) -- Kelly Criterion position sizing
- [spread_screen](../screens/spread_screen.md) -- spread and execution cost analysis

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
