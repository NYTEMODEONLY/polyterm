# Parlay Calculator

> Combine multiple bets into a parlay for higher potential payouts.

## Overview

The Parlay screen calculates combined probability, odds, and expected payout for multi-leg parlay bets. All legs must win for the parlay to pay out. Supports 2-10 legs and includes a generic CLOB V2 protocol fee estimate.

## Access

- **Menu shortcut**: `16`, `parlay`
- **Menu path**: Page 1 → Parlay Calculator

## What It Shows

Two modes of operation:

1. **Interactive mode** -- guided step-by-step parlay builder (recommended)
2. **Quick calculation** -- enter comma-separated probabilities and a bet amount for immediate results

The output includes combined probability, decimal and American odds, expected value, risk level, and fee-adjusted payouts.

## Navigation / Keyboard Shortcuts

Standard menu selection (`1`, `2`, `q` to quit). Probabilities can be entered as decimals (0.65) or percentages (65) -- values above 1 are auto-converted.

## CLI Commands

| Option | CLI command |
|--------|-------------|
| Interactive | `polyterm parlay -i` |
| Quick calc | `polyterm parlay --markets <probs> --amount <amount>` |

Example:

```bash
polyterm parlay --markets 0.65,0.70,0.80 --amount 100
```

## Data Sources

- Pure calculation (no API calls needed for quick mode)
- Gamma REST API when interactive mode looks up live market prices

## Related Screens

- [Odds Converter](../screens/odds_screen.md)
- [Fees Calculator](../screens/fees.md)
- [Position Tracker](../screens/position_screen.md)

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
