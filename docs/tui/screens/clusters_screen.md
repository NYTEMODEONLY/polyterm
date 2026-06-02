# Clusters Screen

> Detect wallets likely controlled by the same entity.

## Overview

The Clusters screen runs wallet cluster detection to identify groups of wallets that may belong to the same person or organization. It analyzes timing correlation, market overlap, and trade size patterns to produce a confidence score for each detected cluster.

## Access

- **Menu shortcut**: `cl` or `clusters`
- **Menu path**: Type shortcut from either page

## What It Shows

- Detected wallet clusters with confidence scores (0-100)
- Detection signals: timing correlation, market overlap (Jaccard similarity), size patterns
- Risk levels: High (70+), Medium (40-69), Low (0-39)

## Navigation / Keyboard Shortcuts

- **1** - Detect clusters with default settings
- **2** - Detect clusters with a custom minimum score threshold
- **b** - Back to menu
- Ctrl+C returns to menu during execution

## CLI Command

```bash
polyterm clusters
polyterm clusters --min-score <score>
```

## Data Sources

- CLOB API / Gamma API (trade data for wallet analysis)

## Related Screens

- [Whales](../screens/whales_screen.md) - track high-volume wallet activity
- [Copy Trading](../screens/follow_screen.md) - follow specific wallets

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
