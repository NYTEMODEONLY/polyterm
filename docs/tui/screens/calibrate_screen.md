# Calibrate Screen

> Track and measure the accuracy of your probability estimates.

## Overview

The Calibrate screen helps you improve as a forecaster by logging probability predictions, resolving them when outcomes are known, and viewing calibration statistics that show how well your estimates match reality.

## Access

- **Menu shortcut**: `cb`, `calibrate`
- **Menu path**: Extended shortcuts menu

## What It Shows

A four-option menu:

1. **View calibration stats** -- how accurate your predictions have been
2. **Log a new prediction** -- record a probability estimate for a market
3. **Resolve a prediction** -- mark a prediction as correct or incorrect
4. **List all predictions** -- view all logged predictions

## Navigation / Keyboard Shortcuts

- `1`-`4` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Stats | `polyterm calibrate --stats` |
| Add prediction | `polyterm calibrate --add` |
| Resolve | `polyterm calibrate --resolve` |
| List all | `polyterm calibrate --list` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)

## Related Screens

- [attribution_screen](../screens/attribution_screen.md) -- performance attribution
- [benchmark_screen](../screens/benchmark_screen.md) -- performance benchmarking

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
