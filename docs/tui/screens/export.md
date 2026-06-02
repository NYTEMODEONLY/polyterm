# Data Export

> Export market data to JSON or CSV files.

## Overview

The Export screen provides a guided wizard for exporting market data to local files. It walks you through selecting a market, choosing a format (JSON or CSV), and specifying an output filename. The exported file is saved to the current working directory by default.

## Access

- **Menu shortcut**: `7` or `e`
- **Menu path**: Page 1 menu item 7

## What It Shows

A step-by-step export flow:

1. Prompts for a market ID or search term
2. Asks for output format (JSON or CSV, defaults to JSON)
3. Asks for output filename (defaults to `export.json` or `export.csv`)
4. Runs the export and displays the absolute path of the saved file

## Navigation / Keyboard Shortcuts

No special keyboard shortcuts. This is a sequential prompt-based flow.

## CLI Command

```bash
polyterm export --market <market> --format json --output export.json
polyterm export --market <market> --format csv --output data.csv
```

## Data Sources

- Gamma REST API for market data
- CLOB API as fallback (via APIAggregator)

## Related Screens

- [History](../screens/history.md) -- view market data before exporting
- [Groups](../screens/groups.md) -- organize markets you may want to export

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
