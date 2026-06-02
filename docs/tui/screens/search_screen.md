# Search Screen

> Advanced market search with filters for volume, price, liquidity, and more.

## Overview

The Search screen launches the interactive market search tool, allowing users to find markets using advanced filters. It provides a streamlined entry point to the `search -i` CLI command from within the TUI.

## Access

- **Menu shortcut**: `sr`, `search`
- **Menu path**: Page 2 (Search)

## What It Shows

A header panel describing the search tool, then launches the interactive search CLI which supports filtering by:

- Category
- Volume and liquidity thresholds
- Price range
- Resolution date (ending soon)
- Multiple sort options (volume, liquidity, price, recent)

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. Interaction is handled by the interactive CLI subprocess.

## CLI Command

```bash
polyterm search -i
```

## Data Sources

- Gamma REST API (market listings and metadata)

## Related Screens

- [stats_screen](../screens/stats_screen.md) -- detailed statistics for a specific market
- [similar_screen](../screens/similar_screen.md) -- find markets related to a given market

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
