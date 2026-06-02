# Rewards Screen

> Estimate your Polymarket holding and liquidity rewards.

## Overview

The Rewards screen estimates your holding rewards based on Polymarket's 4% APY program. Qualifying positions must be in the 20-80 cent price range and held for at least 24 hours. The screen shows daily, weekly, monthly, and yearly reward projections along with liquidity provision eligibility.

## Access

- **Menu shortcut**: `rw` or `rewards`
- **Menu path**: Page 2 -> (shortcut-only, not a numbered item)

## What It Shows

A menu with two options:

1. **View reward estimates** -- shows projected rewards for qualifying positions
2. **JSON output** -- same data in JSON format for programmatic use

Reward output includes per-position eligibility, estimated APY earnings, and total projections across time horizons.

## Navigation / Keyboard Shortcuts

- Enter `1` for standard output, `2` for JSON
- Enter `b` to return to the main menu
- `Ctrl+C` returns to the menu

## CLI Commands

| Option | Command |
|--------|---------|
| Standard view | `polyterm rewards` |
| JSON output | `polyterm rewards --format json` |

## Data Sources

- Data API (`data-api.polymarket.com`) for wallet positions
- Gamma API for current market prices
- Local config (`~/.polyterm/config.toml`) for wallet address

## Related Screens

- [Portfolio](../screens/export.md)

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
