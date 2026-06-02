# Fee & Slippage Calculator

> Calculate the true cost of trades including fees and slippage.

## Overview

The Fees screen launches an interactive calculator that breaks down trading costs on Polymarket. It covers dynamic CLOB V2 protocol fee estimates, estimates slippage from order book depth, projects net profit/loss, and includes Polygon network gas fee estimates.

## Access

- **Menu shortcut**: `fee` or `fees`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

An interactive calculator that computes:

- Dynamic CLOB V2 protocol fee estimate
- Slippage estimation based on order book depth
- Net profit/loss projections after all costs
- Gas fee estimates for Polygon network transactions

## Navigation / Keyboard Shortcuts

No special keyboard shortcuts. This is an interactive prompt-based calculator.

## CLI Command

```bash
polyterm fees -i
```

## Data Sources

- CLOB API for order book data and fee schedule context
- Gamma API market metadata for fee schedule context
- Polygon network gas estimates

## Related Screens

- [Exit Strategy](../screens/exit.md) -- factor fees into exit targets
- [Hot Markets](../screens/hot.md) -- check costs on active markets

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
