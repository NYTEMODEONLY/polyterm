# Market History

> View CLOB price history for a market. Refuses instead of inventing a path.

## Overview

The History screen looks up a market, asks for a time period, and launches `polyterm history` against CLOB `GET /prices-history`. It is view-only.

The screen does not pass `--demo`. If CLOB token IDs or history points are missing, the CLI refuses instead of drawing a random walk.

## Access

- **Menu shortcut**: `hist` or `history`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A two-step prompt flow, then the CLI output:

1. **Market selection** -- enter a Gamma search term, slug, or id
2. **Time period** -- last day, last week (default), last month, or all time

The screen states that it uses CLOB `/prices-history` before the CLI runs. Table output includes source flags (`uses_historical_data`, `source`) and an ASCII chart of the real series when available.

## Navigation / Keyboard Shortcuts

- `1`-`4` -- Select time period
- No additional keyboard shortcuts; prompt-based flow

## CLI Command

```bash
polyterm history <market> --period week --chart
polyterm history <market> --period day --chart
polyterm history <market> --period month --chart
polyterm history <market> --period all --chart
```

Labeled demo is CLI-only:

```bash
polyterm history <market> --demo --format json
```

## Data Sources

- Gamma Markets REST API for search and CLOB token IDs
- CLOB REST `GET /prices-history` with `market=<CLOB token ID>`
- No local snapshot fallback and no synthetic default path

## Related Screens

- [Chart](chart_screen.md) -- ASCII charts that also prefer CLOB history
- [Hot Markets](hot.md) -- markets with significant recent movement

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm `polyterm/tui/screens/history_screen.py` still exists.
- Keep the TUI from auto-enabling `--demo`.
- Keep data-source notes on CLOB token IDs versus Gamma market IDs.
- Run `./test_all_commands.sh` and `.venv/bin/python scripts/validate_docs.py`.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Examples should be copy-pasteable from the repository root unless stated otherwise.
- Pages for view-only workflows should say so.
- Pages that depend on live market data should name Gamma and CLOB as the source.
