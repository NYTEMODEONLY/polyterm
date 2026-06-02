# Market Screener Screen

> Filter markets by multiple criteria.

## Overview

The Market Screener screen provides a way to scan for markets matching specific conditions. It offers both a full interactive mode and quick-scan presets for common queries like high-volume markets, big movers, and markets ending soon.

## Access

- **Menu shortcut**: `scr` or `screener`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A menu with four options:

1. **Interactive mode** -- full filter builder with prompts for volume, price range, category, and more
2. **Quick scan: high volume** -- markets with volume above $10,000, sorted by volume
3. **Quick scan: big movers** -- markets with price change above 5%, sorted by change
4. **Quick scan: ending soon** -- markets resolving within 7 days, sorted by end date

## Navigation / Keyboard Shortcuts

- Enter a number `1`-`4` to select a scan type
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Interactive | `polyterm screener -i` |
| High volume | `polyterm screener -v 10000 -s volume` |
| Big movers | `polyterm screener --min-change 5 -s change` |
| Ending soon | `polyterm screener --ending-within 7 -s end_date` |

## Data Sources

- Gamma API for market listings, volume, and pricing data

## Related Screens

- [Presets Screen](../screens/presets_screen.md)
- [Calendar Screen](../screens/calendar_screen.md)

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
