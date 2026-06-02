# Quick Trade Screen

> Analyze trades and get direct Polymarket links.

## Overview

The Quick Trade screen helps you prepare trades by analyzing entry price, shares, fees, and P&L scenarios. It generates a direct link to Polymarket for execution. This screen does not execute trades -- it provides analysis and a convenient link to the Polymarket UI.

## Access

- **Menu shortcut**: `qt` or `quicktrade`
- **Menu path**: Page 2 -> Quick Trade

## What It Shows

A menu with two options:

1. **Interactive trade preparation** -- guided prompts for market, side, and amount
2. **Search for a market** -- enter a market name, side (yes/no), and dollar amount directly

After selection, displays trade analysis including entry price, share count, fee breakdown, breakeven price, and projected P&L.

## Navigation / Keyboard Shortcuts

- Enter `1` for interactive mode, `2` for direct search
- Enter `b` to return to the main menu
- `Ctrl+C` returns to the menu

## CLI Commands

| Option | Command |
|--------|---------|
| Interactive | `polyterm quicktrade -i` |
| Direct | `polyterm quicktrade -m <market> -s <yes/no> -a <amount>` |

## Data Sources

- Gamma API for market data and current pricing
- CLOB API for order book depth and fee calculations

## Related Screens

- [Quick Actions Screen](../screens/quick_screen.md)
- [Fees Screen](../screens/fees.md)

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
