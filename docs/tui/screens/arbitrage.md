# Arbitrage Screen

> Scan for arbitrage opportunities across Polymarket and optionally Kalshi.

## Overview

The Arbitrage screen scans for pricing inefficiencies where buying both sides of a market costs less than the guaranteed payout. It prompts for scan parameters (minimum spread, result limit, cross-platform inclusion) then invokes the CLI arbitrage scanner.

## Access

- **Menu shortcut**: `9`, `arb`
- **Menu path**: Page 1 item 9 (Arbitrage)

## What It Shows

After configuring scan parameters, displays arbitrage opportunities including:

- Intra-market opportunities (YES + NO < $0.975)
- Correlated market divergences
- Cross-platform Polymarket vs Kalshi spreads (optional)

## Navigation / Keyboard Shortcuts

Interactive prompts before scan:

1. **Minimum spread %** -- default 2.5%
2. **Max opportunities** -- default 10, max 50
3. **Include Kalshi** -- y/n, default n

## CLI Command

```
polyterm arbitrage --min-spread=SPREAD --limit=N [--include-kalshi]
```

The spread value entered as a percentage is converted to decimal (e.g., 2.5 becomes 0.025).

## Data Sources

- Gamma REST API (market prices)
- CLOB REST API (fallback)
- Kalshi API (if cross-platform enabled)
- Optional: live WebSocket mid-prices via `OrderBookAnalyzer`

## Related Screens

- [analytics](../screens/analytics.md) -- market analytics and trending

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
