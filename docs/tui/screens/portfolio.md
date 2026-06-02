# Portfolio

> View your Polymarket positions by wallet address.

## Overview

The Portfolio screen displays on-chain positions for a given wallet address. You can enter a wallet address manually or use the one saved in your config file. This is a read-only view -- no private keys are needed.

## Access

- **Menu shortcut**: `6` or `p`
- **Menu path**: Page 1 → Portfolio

## What It Shows

Prompts for a wallet address (or uses the configured default), then displays:

- Current open positions
- Position values and P&L
- Market details for each held position

## Navigation / Keyboard Shortcuts

No special keyboard shortcuts. Enter a wallet address or press Enter to use the configured default. Ctrl+C to stop.

## CLI Command

```bash
polyterm portfolio [--wallet <address>]
```

## Data Sources

- Data API (`data-api.polymarket.com`) for wallet positions
- Gamma REST API for market metadata
- Config file (`~/.polyterm/config.toml`) for default wallet address

## Related Screens

- [My Wallet](../screens/mywallet.md)
- [Position Tracker](../screens/position_screen.md)
- [P&L Tracker](../screens/pnl_screen.md)

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
