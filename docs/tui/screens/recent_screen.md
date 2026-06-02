# Recent Screen

> View markets you have recently interacted with.

## Overview

The Recent screen shows your recently viewed markets, letting you quickly return to markets you were researching. Markets are automatically tracked as you use PolyTerm, and view counts are recorded for frequently accessed markets.

## Access

- **Menu shortcut**: `rec` or `recent`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A list of recently viewed markets with timestamps and view counts, ordered by most recent access. Provides a quick way to resume research on markets you have been following.

## Navigation / Keyboard Shortcuts

No screen-level shortcuts. The screen runs a single CLI command and displays its output.

## CLI Command

```bash
polyterm recent
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) -- `recently_viewed` table

## Related Screens

- [Bookmarks](../screens/notes.md)

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
