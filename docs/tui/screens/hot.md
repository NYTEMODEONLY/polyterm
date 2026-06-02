# Hot Markets

> See the biggest market movers right now.

## Overview

The Hot Markets screen shows which prediction markets are experiencing the most price movement or volume activity. You can filter to see all movers, only gainers, only losers, or sort by highest volume. Useful for spotting trending markets and potential trading opportunities.

## Access

- **Menu shortcut**: `hot`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A menu with four view options:

1. **Top movers (all)** -- markets with the largest price changes in either direction
2. **Gainers only** -- markets with the biggest price increases
3. **Losers only** -- markets with the biggest price drops
4. **Highest volume** -- markets ranked by trading volume

## Navigation / Keyboard Shortcuts

- `1` -- Top movers (all)
- `2` -- Gainers only
- `3` -- Losers only
- `4` -- Highest volume
- `b` -- Back to main menu

## CLI Command

```bash
polyterm hot              # Top movers (all)
polyterm hot --gainers    # Gainers only
polyterm hot --losers     # Losers only
polyterm hot --volume     # Highest volume
```

## Data Sources

- Gamma REST API for market data and price changes
- CLOB API as fallback (via APIAggregator)

## Related Screens

- [History](../screens/history.md) -- dig into price history of a hot market
- [Fees](../screens/fees.md) -- calculate costs before trading a hot market

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
