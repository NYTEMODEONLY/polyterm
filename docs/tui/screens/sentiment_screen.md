# Sentiment Screen

> Analyze market sentiment from multiple market signals.

## Overview

The Sentiment screen provides a multi-signal sentiment analysis for a specific market. It combines momentum, volume, order book, trade activity, and whale activity into a composite sentiment view. The user searches for a market by name, and the analysis runs against it.

## Access

- **Menu shortcut**: `sent`, `sentiment`
- **Menu path**: Page 2 (Sentiment)

## What It Shows

After prompting for a market search term, it displays a sentiment analysis that combines:

- Momentum signals
- Volume signals
- Order book analysis
- Trade activity
- Whale activity

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. The user enters a market search term at the prompt; leaving it blank returns to the menu.

## CLI Command

```bash
polyterm sentiment --market "<search term>"
```

## Data Sources

- Gamma REST API (market data)
- CLOB API (order book, trade activity)

## Related Screens

- [signals_screen](../screens/signals_screen.md) -- entry/exit signals based on multiple factors
- [stats_screen](../screens/stats_screen.md) -- technical indicators and statistics

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
