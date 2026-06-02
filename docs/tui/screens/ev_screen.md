# EV Screen

> Calculate whether a trade has positive expected value.

## Overview

The EV (Expected Value) screen helps determine if a bet is mathematically favorable by comparing your estimated probability of an outcome against the market price. It offers both a guided interactive mode and a quick calculation mode for direct input.

## Access

- **Menu shortcut**: `ev`
- **Menu path**: Type shortcut from either page

## What It Shows

- Expected value per dollar wagered
- Edge calculation (your probability vs. market implied probability)
- Whether the trade is +EV or -EV

## Navigation / Keyboard Shortcuts

- **1** - Interactive mode (recommended; guided step-by-step)
- **2** - Quick calculation (provide market name and your probability directly)
- **b** - Back to menu

## CLI Command

```bash
polyterm ev -i                        # Interactive mode
polyterm ev -m <market> -p <probability>  # Quick calculation
```

## Data Sources

- Gamma REST API (current market prices for implied probability)

## Related Screens

- [Predictions](../screens/predictions_screen.md) - signal-based prediction analysis
- [Size](../screens/size_screen.md) - Kelly Criterion position sizing
- [Simulate](../screens/simulate_screen.md) - P&L calculator

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
