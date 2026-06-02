# Streak Tracker

> Track winning and losing streaks across your prediction market trades.

## Overview

The Streak Tracker screen shows your current and historical trading streaks. It helps identify momentum in your trading performance and patterns of consecutive wins or losses.

## Access

- **Menu shortcut**: `stk` or `streak`
- **Menu path**: Page 2 → Streak Tracker

## What It Shows

Two viewing modes:

1. **Current streak status** -- Your active win/loss streak summary.
2. **Detailed streak history** -- Full breakdown of past streaks over time.

## Navigation / Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Current streak status |
| `2` | Detailed streak history |
| `b` | Back to main menu |

## CLI Command

```bash
# Current streak status
polyterm streak

# Detailed streak history
polyterm streak --detailed
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for trade history

## Related Screens

- [Journal](../screens/journal_screen.md)
- [Timing Analysis](../screens/timing_screen.md)

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
