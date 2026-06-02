# News Screen

> Latest headlines from crypto and prediction market news sources.

## Overview

The News Screen aggregates RSS headlines from The Block, CoinDesk, and Decrypt. It supports viewing recent news, breaking news within a shorter time window, or news matched to a specific market by keyword.

## Access

- **Menu shortcut**: `nw`, `news`
- **Menu path**: Extended shortcuts menu

## What It Shows

An options menu with three modes:

1. **Latest news (24h)** -- headlines from the past 24 hours
2. **Breaking news (6h)** -- headlines from the past 6 hours only
3. **News for a market** -- prompts for a search term and shows matching articles

## Navigation / Keyboard Shortcuts

- `1`-`3` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Latest news | `polyterm news` |
| Breaking news | `polyterm news --hours 6` |
| Market-specific | `polyterm news --market <term>` |

## Data Sources

- RSS feeds (The Block, CoinDesk, Decrypt)
- 5-minute cache to reduce repeated fetches

## Related Screens

- [monitor](../screens/monitor.md) -- market monitoring for price changes alongside news

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
