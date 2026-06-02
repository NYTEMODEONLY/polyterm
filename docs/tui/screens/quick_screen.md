# Quick Actions Screen

> Fast access to common trading tasks.

## Overview

The Quick Actions screen provides a streamlined menu for common market lookups. After selecting an action type, you enter a market name and the corresponding quick command runs immediately. This is designed for rapid, single-purpose queries without navigating through full-featured screens.

## Access

- **Menu shortcut**: `qk` or `quick`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A numbered menu with five actions:

1. **Quick price check** -- current price for a market
2. **Quick buy calculation** -- cost/return analysis for buying
3. **Quick sell calculation** -- cost/return analysis for selling
4. **Quick market info** -- summary information about a market
5. **Quick add to watchlist** -- add a market to your watchlist

After selecting an action, you are prompted for a market name.

## Navigation / Keyboard Shortcuts

- Enter a number `1`-`5` to select an action
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Price check | `polyterm quick price <market>` |
| Buy calculation | `polyterm quick buy <market>` |
| Sell calculation | `polyterm quick sell <market>` |
| Market info | `polyterm quick info <market>` |
| Add to watchlist | `polyterm quick watch <market>` |

## Data Sources

- Gamma API for market data and pricing
- Local SQLite database for watchlist storage

## Related Screens

- [Quick Trade Screen](../screens/quicktrade_screen.md)

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
