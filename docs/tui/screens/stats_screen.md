# Stats Screen

> View volatility, trends, RSI, and other technical indicators for a market.

## Overview

The Stats screen displays detailed market statistics and technical analysis for a specific market. It calculates volatility, trend direction, RSI, momentum, price range, and certainty measurements from historical price data.

## Access

- **Menu shortcut**: `st`, `stats`
- **Menu path**: Page 2 (Stats)

## What It Shows

After prompting for a market ID or search term, it displays:

- **Volatility** -- standard deviation of returns
- **Trend** -- linear regression slope (direction and strength)
- **RSI** -- Relative Strength Index (14-period)
- **Momentum** -- accelerating or decelerating
- **Price Range** -- high, low, and range
- **Certainty** -- distance from 50% (how decisive the market is)

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. The user enters a market identifier at the prompt; leaving it empty returns to the menu.

## CLI Command

```bash
polyterm stats -m "<market>"
```

## Data Sources

- Gamma REST API (market metadata)
- CLOB API (price history)
- Local SQLite database (historical snapshots as fallback)

## Related Screens

- [sentiment_screen](../screens/sentiment_screen.md) -- multi-signal sentiment analysis
- [signals_screen](../screens/signals_screen.md) -- trade entry/exit signals
- [search_screen](../screens/search_screen.md) -- find markets to analyze

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
