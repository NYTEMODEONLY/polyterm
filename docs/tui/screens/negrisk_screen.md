# NegRisk Screen

> Scan multi-outcome markets for guaranteed-profit arbitrage opportunities.

## Overview

The NegRisk Screen scans multi-outcome (NegRisk) markets for arbitrage opportunities. When the sum of all YES prices in a multi-outcome market is less than $1.00, buying all outcomes guarantees a profit. The screen offers a default scan or a custom minimum spread setting.

## Access

- **Menu shortcut**: `nr`, `negrisk`
- **Menu path**: Extended shortcuts menu

## What It Shows

An options menu with two modes:

1. **Scan with default settings** -- uses the default minimum spread
2. **Custom minimum spread** -- prompts for a spread value (e.g., 0.03)

## Navigation / Keyboard Shortcuts

- `1`-`2` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Default scan | `polyterm negrisk` |
| Custom spread | `polyterm negrisk --min-spread <value>` |

## Data Sources

- Gamma REST API (multi-outcome market listings)
- CLOB API (outcome prices)

## Related Screens

- [liquidity_screen](../screens/liquidity_screen.md) -- compare market liquidity and spreads

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
