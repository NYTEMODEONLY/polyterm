# Monitor Screen

> Polling-based market monitoring with category and sub-category filtering.

## Overview

The Monitor Screen provides a guided setup for the market monitor CLI command. It lets you configure the number of markets, category/sub-category filters, refresh rate, and active-only filtering before launching a continuously refreshing market table.

## Access

- **Menu shortcut**: `1`, `mon`
- **Menu path**: Page 1 -> Monitor

## What It Shows

An interactive configuration flow:

1. **Market count** -- how many markets to display (default: 20)
2. **Category selection** -- All Markets, Sports, Crypto, or Politics
3. **Sub-category** -- drill-down options per category (e.g., Sports -> NFL/NBA/MLB/NHL/Soccer/Golf/Tennis/UFC/F1)
4. **Refresh rate** -- seconds between updates (default: 5)
5. **Active only** -- whether to filter to active markets only (default: yes)

After configuration, the monitor runs continuously until stopped with `Ctrl+C`.

## Navigation / Keyboard Shortcuts

- Numbered selections for category and sub-category
- `Ctrl+C` to stop the monitor

## CLI Command

```bash
polyterm monitor --limit <n> --refresh <sec> [--category <cat>] [--active-only]
```

## Data Sources

- Gamma REST API (market listings, prices, volumes)

## Related Screens

- [live_monitor](../screens/live_monitor.md) -- WebSocket-based real-time monitoring
- [liquidity_screen](../screens/liquidity_screen.md) -- liquidity comparison across markets

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
