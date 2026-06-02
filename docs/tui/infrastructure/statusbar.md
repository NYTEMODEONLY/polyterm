# Status Bar

> Status bar display showing connection state, market count, and timestamp.

## Overview

Provides two functions for rendering a bottom status bar with API connection status, tracked market count, and the current time. One function prints directly to a Rich console; the other returns a formatted string for embedding in other layouts.

## Key Classes / Functions

### `display_status_bar(console, market_count=0, connected=True)`

Prints a centered status bar to the console with a blue background. Shows a connection indicator, market count, and `HH:MM:SS` timestamp.

### `create_status_string(connected=True, market_count=0, extra="") -> str`

Returns the same information as a pipe-delimited string without printing. Accepts an optional `extra` parameter appended as an additional segment.

## Configuration

None. All parameters are passed at call time.

## Architecture Role

Used by screens that need to show persistent status information (e.g., live monitors, watch screens). The two-function design allows both direct rendering and integration into Rich `Live` or `Layout` displays.

## Related Modules

- [controller](../infrastructure/controller.md) -- main loop that hosts screens using the status bar
- [themes](../infrastructure/themes.md) -- defines the `status_bar` style key (e.g. `"on blue"`)

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
