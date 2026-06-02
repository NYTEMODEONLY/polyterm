# Analyze Screen

> Portfolio exposure and risk analysis.

## Overview

The Analyze screen shows portfolio analytics including category exposure, concentration risk, and recommendations for portfolio balance. It launches the CLI command directly without additional prompts.

## Access

- **Menu shortcut**: `an`, `analyze`
- **Menu path**: Extended shortcuts menu

## What It Shows

- Category exposure breakdown
- Concentration risk assessment
- Recommendations for improving portfolio balance

## Navigation / Keyboard Shortcuts

No in-screen navigation. The screen runs the CLI command and returns.

## CLI Command

```
polyterm analyze
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for tracked positions

## Related Screens

- [analytics](../screens/analytics.md) -- market-level analytics (trending, correlations)
- [benchmark_screen](../screens/benchmark_screen.md) -- compare performance to market averages
- [attribution_screen](../screens/attribution_screen.md) -- performance attribution analysis

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
