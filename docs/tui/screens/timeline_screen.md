# Event Timeline

> Visual timeline of upcoming market resolutions.

## Overview

The Event Timeline screen displays a chronological view of markets approaching their resolution dates. It helps traders plan exits and identify opportunities around upcoming events. Supports filtering by time window or bookmarked markets.

## Access

- **Menu shortcut**: `tl` or `timeline`
- **Menu path**: Page 2 → Timeline

## What It Shows

A time-ordered list of markets grouped by resolution date, with countdown indicators showing how soon each market resolves.

## Navigation / Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Next 7 days |
| `2` | Next 30 days (default) |
| `3` | Next 90 days |
| `4` | Bookmarked markets only |
| `b` | Back to main menu |

## CLI Command

```bash
# Next 30 days (default)
polyterm timeline --days 30

# Next 7 days
polyterm timeline --days 7

# Bookmarked markets only
polyterm timeline --bookmarked
```

## Data Sources

- Gamma REST API for market resolution dates
- Local SQLite database for bookmarked market filtering

## Related Screens

- [Calendar](../screens/alertcenter_screen.md)
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
