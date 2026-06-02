# Risk Assessment Screen

> Evaluate markets on six weighted risk factors with A-F grades.

## Overview

The Risk Assessment screen scores a market across six dimensions: resolution clarity, liquidity quality, time to resolution, volume patterns (wash trading indicators), spread, and category risk. Each market receives a letter grade (A through F) based on a weighted composite score, along with specific warnings and recommendations.

## Access

- **Menu shortcut**: `14` or `risk`
- **Menu path**: Page 2 -> Risk

## What It Shows

After entering a market ID or search term, displays:

- Overall risk grade (A-F) with numeric score
- Breakdown of all six risk factors with individual scores
- Risk warnings for flagged areas
- Actionable recommendations

## Navigation / Keyboard Shortcuts

- Enter a market name or ID when prompted
- Press Enter with no input to return to the menu
- Press Enter after results to return to the menu

## CLI Command

```bash
polyterm risk --market <market>
```

## Data Sources

- Gamma API for market metadata, liquidity, and volume
- Wash trade detection engine for volume quality analysis
- UMA oracle data for resolution clarity assessment

## Related Screens

- [Analyze Screen](../screens/analyze_screen.md)
- [Fees Screen](../screens/fees.md)

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
