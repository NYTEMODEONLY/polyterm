# Quick Trade Calculator

> Analyze fees, slippage, breakeven, and profit scenarios before trading.

## Overview

The Quick Trade Calculator provides a comprehensive pre-trade analysis for any market. It calculates fees, slippage estimates, breakeven price, and profit/loss scenarios so you can evaluate a trade before executing it. This screen does not execute trades -- it provides analysis only.

## Access

- **Menu shortcut**: `tr` or `trade`
- **Menu path**: Page 2 → Quick Trade Calculator

## What It Shows

- Entry price and share count
- Dynamic CLOB V2 protocol fee estimate
- Slippage estimate from order book
- Breakeven price
- Profit if win / loss if lose scenarios
- Risk/reward ratio

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Market search term
2. Side (`yes` or `no`)
3. Trade amount in dollars (default: $100)

## CLI Command

```bash
polyterm trade --market "bitcoin" --side yes --amount 100
```

## Data Sources

- Gamma REST API for market data
- CLOB API for order book depth and slippage estimation

## Related Screens

- [Fees Calculator](../screens/exit.md)
- [Position Size Calculator](../screens/analyze_screen.md)

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
