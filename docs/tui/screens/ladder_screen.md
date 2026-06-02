# Ladder Screen

> Visual order book depth at each price level for a market.

## Overview

The Ladder Screen displays a price ladder view of the order book for a given market. It shows liquidity at each price level and lets you choose whether to view the YES side, NO side, or both.

## Access

- **Menu shortcut**: `lad`, `ladder`
- **Menu path**: Extended shortcuts menu

## What It Shows

A price ladder visualization showing order book depth at each price level for the selected market. The user is prompted for:

1. **Market** -- enter a market name or identifier
2. **Side** -- choose YES only, NO only, or both sides

## Navigation / Keyboard Shortcuts

- Select side: `1` (Both), `2` (YES only), `3` (NO only)

## CLI Commands

| Option | Command |
|--------|---------|
| Both sides | `polyterm ladder <market> --side both` |
| YES only | `polyterm ladder <market> --side yes` |
| NO only | `polyterm ladder <market> --side no` |

## Data Sources

- CLOB API (order book data)

## Related Screens

- [orderbook_screen](../screens/orderbook_screen.md) -- real-time order book with live WebSocket feed
- [liquidity_screen](../screens/liquidity_screen.md) -- compare liquidity across markets

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
