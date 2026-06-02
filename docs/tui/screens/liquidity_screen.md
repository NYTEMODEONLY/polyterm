# Liquidity Screen

> Compare liquidity scores and spreads across markets.

## Overview

The Liquidity Screen lets you compare liquidity conditions across Polymarket markets. You can sort by liquidity score or spread, filter by category, or focus on high-volume markets only.

## Access

- **Menu shortcut**: `liq`, `liquidity`
- **Menu path**: Extended shortcuts menu

## What It Shows

An options menu with four views:

1. **All markets - sort by score** -- ranks markets by overall liquidity score
2. **All markets - sort by spread** -- ranks markets by bid-ask spread
3. **Filter by category** -- prompts for a category, then shows liquidity for that category
4. **High volume only (>$10k)** -- shows only markets with volume above $10,000, sorted by score

## Navigation / Keyboard Shortcuts

- `1`-`4` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Sort by score | `polyterm liquidity -s score` |
| Sort by spread | `polyterm liquidity -s spread` |
| Filter by category | `polyterm liquidity -c <category>` |
| High volume only | `polyterm liquidity -v 10000 -s score` |

## Data Sources

- Gamma REST API (market data, volumes)
- CLOB API (order book spreads)

## Related Screens

- [ladder_screen](../screens/ladder_screen.md) -- price ladder for a single market
- [monitor](../screens/monitor.md) -- market monitoring with category filters

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
