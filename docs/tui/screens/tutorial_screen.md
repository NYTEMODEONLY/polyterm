# Interactive Tutorial

> Step-by-step guide to prediction markets and PolyTerm features.

## Overview

The Tutorial screen launches an interactive walkthrough designed for new users. It covers how prediction markets work, understanding prices as probabilities, tracking whales, finding arbitrage, and using PolyTerm's core features.

## Access

- **Menu shortcut**: `t`, `tut`, or `tutorial`
- **Menu path**: Page 1 → Tutorial (via `t` shortcut)

## What It Shows

A multi-step guided tutorial covering:

- How prediction markets work
- Understanding prices as probabilities
- Tracking whales and smart money
- Finding arbitrage opportunities
- Using PolyTerm's features

## Navigation / Keyboard Shortcuts

The screen asks for confirmation before starting. If declined, it returns to the main menu with a reminder that the tutorial can be run later from the CLI.

## CLI Command

```bash
polyterm tutorial
```

## Data Sources

- No external data sources; tutorial content is self-contained

## Related Screens

- [Glossary](../screens/alerts_screen.md) -- Prediction market terminology reference

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
