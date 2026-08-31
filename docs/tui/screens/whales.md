# Whale Tracker

> Monitor high-volume markets (Gamma 24h volume heuristic, not trader identity).

## Overview

The Whales screen lists markets by Gamma 24h volume. It does not identify whale wallets or invent trader names. Configurable by minimum 24h volume, lookback prompt (kept for CLI compatibility), and result count.

For wallet-level public trades, run `polyterm whales --wallets`. That path is lagged Data API, not live CLOB.

## Access

- **Menu shortcut**: `3` or `w`
- **Menu path**: Page 1 → Whales (option 3)

## What It Shows

A list of high-volume **markets** (not whale trades), filtered by:

- Minimum 24-hour Gamma volume threshold
- Lookback period in hours (CLI flag; heuristic itself uses Gamma `volume24hr`)
- Maximum number of results

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Minimum 24hr volume (default: $10,000)
2. Lookback period in hours (default: 24)
3. Maximum results to show (default: 20)

Press `Ctrl+C` to stop and return to the menu.

## CLI Command

```bash
polyterm whales --volume --min-amount 10000 --hours 24 --limit 20
polyterm whales --wallets --min-amount 100000 --hours 72
```

## Data Sources

- Gamma REST API `volume24hr` for the default TUI heuristic
- Lagged Data API `/trades` for `polyterm whales --wallets` (not live CLOB)
- CLOB WebSocket / REST polling live in `core/whale_tracker.py`, not this screen

## Related Screens

- [Wallet Tracker](../screens/wallets.md)
- [Copy Trading / Follow](../screens/export.md)
- [Clusters](../screens/alertcenter_screen.md)

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
