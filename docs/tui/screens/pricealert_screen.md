# Price Alert Screen

> Set alerts to notify you when markets hit target prices.

## Overview

The Price Alert screen launches the interactive price alert manager. You can create alerts for specific price targets, list existing alerts, check which alerts have triggered, and remove alerts you no longer need. Alerts are direction-aware (above or below target).

## Access

- **Menu shortcut**: `pa` or `pricealert`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

Launches directly into the `pricealert` CLI command in interactive mode, which provides options to add, list, check, and remove price alerts.

## Navigation / Keyboard Shortcuts

No screen-level shortcuts. Navigation is handled by the interactive CLI prompts.

## CLI Command

```bash
polyterm pricealert -i
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) -- `price_alerts` table
- Gamma API for current market prices when checking alerts

## Related Screens

- [Alerts Screen](../screens/alerts_screen.md)
- [Alert Center Screen](../screens/alertcenter_screen.md)

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
