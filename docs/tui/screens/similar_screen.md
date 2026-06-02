# Similar Screen

> Find markets related to one you are watching.

## Overview

The Similar screen helps users discover markets that are related to a given market. It supports three match types: topic-based similarity, category-based similarity, or both combined. This is useful for finding correlated markets or alternative betting opportunities.

## Access

- **Menu shortcut**: `sml`, `similar`
- **Menu path**: Page 2 (Similar)

## What It Shows

After prompting for a market name and match type, it displays a list of similar markets. The user selects from three match modes:

1. **All** -- matches by both topic and category
2. **Topic only** -- matches by topic/subject similarity
3. **Category only** -- matches by market category

## Navigation / Keyboard Shortcuts

- `1` / `2` / `3` -- select match type (all, topic, category)
- Leaving the market prompt empty returns to the menu

## CLI Command

```bash
polyterm similar "<market name>" --type <all|topic|category>
```

## Data Sources

- Gamma REST API (market listings, categories, topics)

## Related Screens

- [search_screen](../screens/search_screen.md) -- advanced market search with filters
- [sentiment_screen](../screens/sentiment_screen.md) -- sentiment analysis for discovered markets

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
