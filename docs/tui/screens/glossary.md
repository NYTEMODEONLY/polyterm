# Prediction Market Glossary

> Browse and search prediction market terminology.

## Overview

The Glossary screen provides access to a comprehensive dictionary of prediction market terms. You can view all terms at once, search for a specific term, or browse by category. Useful for newcomers learning the vocabulary of prediction markets and Polymarket-specific concepts.

## Access

- **Menu shortcut**: `g`, `gloss`, or `glossary`
- **Menu path**: Page 2 extended shortcuts (also shown in bottom menu bar)

## What It Shows

A menu with three browsing options:

1. **View all terms** -- displays the complete glossary
2. **Search for a term** -- find a specific term by keyword
3. **Browse by category** -- filter terms by category (Core Concepts, Trading, Analysis, Arbitrage, Platforms, Technical, Risk)

## Navigation / Keyboard Shortcuts

- `1` -- View all terms
- `2` -- Search for a term
- `3` -- Browse by category
- `q` -- Return to menu

## CLI Command

```bash
polyterm glossary                        # View all terms
polyterm glossary --search <term>        # Search for a term
polyterm glossary --category <category>  # Browse by category
```

## Data Sources

- Built-in glossary data (no external API calls)

## Related Screens

- [Help](../screens/help.md) -- full feature documentation and shortcuts

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
