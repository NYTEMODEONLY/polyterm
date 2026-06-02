# Help & Documentation

> In-app reference for all features, shortcuts, and CLI commands.

## Overview

The Help screen is a comprehensive reference displayed directly in the TUI (no subprocess). It lists all keyboard shortcuts, describes every feature, shows equivalent CLI commands for power users, and provides API status and external resource links. This is the go-to screen when you need to find a shortcut or understand what a feature does.

## Access

- **Menu shortcut**: `h` or `?`
- **Menu path**: Available from any menu prompt

## What It Shows

Four sections displayed inline:

1. **Keyboard Shortcuts** -- complete table of all TUI shortcuts (1-17 for menu items, plus two-letter shortcuts for every feature)
2. **Features** -- description of every feature with a brief explanation of what it does
3. **CLI Commands** -- equivalent `polyterm` commands for all features, useful for scripting and power users
4. **API Status** -- current status of Gamma API, CLOB API, and Subgraph API
5. **Resources** -- links to GitHub repository, Polymarket docs, and issue tracker

## Navigation / Keyboard Shortcuts

This screen is read-only. Scroll through the output and press Enter when done.

## CLI Command

This screen does not invoke a CLI command. All content is rendered directly using Rich tables and formatted output.

## Data Sources

- No external data sources. All content is hardcoded in the help screen.

## Related Screens

- [Glossary](../screens/glossary.md) -- prediction market terminology

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
