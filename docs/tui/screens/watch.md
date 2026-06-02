# Watch Specific Market

> Monitor a single market with configurable alert thresholds.

## Overview

The Watch screen lets you track a specific market in real time, alerting you when the probability changes by more than a configurable threshold. It accepts either a market search term or a direct Market ID, and runs continuously until stopped. The underlying CLI dashboard keeps status, market metrics, and recent alerts fixed while polling continues.

## Access

- **Menu shortcut**: `4`
- **Menu path**: Page 1 → Watch (option 4)

## What It Shows

A live updating view of a single market's probability, refreshing at a configurable interval. Alerts are triggered when the probability or volume change exceeds the configured threshold. The display includes check count, last check time, current market state, and recent alerts.

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Market search term or Market ID
2. Alert threshold for probability change (default: 5%)
3. Check interval in seconds (default: 10)

Press `Ctrl+C` to stop watching and return to the menu.

## CLI Command

```bash
polyterm watch --market <market_id> --threshold 5 --interval 10
```

## Data Sources

- Gamma REST API for market data polling
- CLOB API as fallback

## Related Screens

- [Watchdog Monitor](../screens/watchdog_screen.md)
- [Live Monitor](../screens/alerts_screen.md)
- [Price Alerts](../screens/alertcenter_screen.md)

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
