# Signals Screen

> Entry/exit signals based on multiple market factors.

## Overview

The Signals screen provides trade signal analysis for prediction markets. Users can analyze a specific market for signals, or scan across markets for entry signals, exit signals, or both. Signals are derived from momentum, volume, whale activity, smart money, and technical indicators.

## Access

- **Menu shortcut**: `sig`, `signals`
- **Menu path**: Page 2 (Signals)

## What It Shows

A submenu with four operations:

1. **Analyze specific market** -- signals for a single market by name
2. **Scan for entry signals** -- find markets with buy signals
3. **Scan for exit signals** -- find markets with sell signals
4. **Scan all signals** -- find all entry and exit signals

## Navigation / Keyboard Shortcuts

- `1` -- Analyze a specific market (prompts for market name)
- `2` -- Scan entry signals
- `3` -- Scan exit signals
- `4` -- Scan all signals
- `b` -- Back to main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Analyze market | `polyterm signals --market "<name>"` |
| Entry scan | `polyterm signals --scan --type entry` |
| Exit scan | `polyterm signals --scan --type exit` |
| All signals | `polyterm signals --scan` |

## Data Sources

- Gamma REST API (market data)
- CLOB API (price history, order book)
- Local SQLite database (historical snapshots)

## Related Screens

- [sentiment_screen](../screens/sentiment_screen.md) -- composite sentiment analysis
- [stats_screen](../screens/stats_screen.md) -- technical indicators (RSI, momentum)

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
