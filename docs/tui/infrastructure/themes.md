# Themes

> Color theme definitions for the TUI interface.

## Overview

Defines a set of named color themes as dictionaries of Rich style strings. Each theme provides consistent styling for the logo, menu, panels, status bar, and semantic colors (success, warning, error, info). Themes use only standard Rich color names for broad terminal compatibility.

## Key Classes / Functions

### `THEMES`

A dictionary of four built-in themes, each mapping style keys to Rich style strings:

| Theme | Character |
|-------|-----------|
| `default` | Cyan logo, yellow titles, green borders, blue status bar |
| `dark` | Blue logo, white titles, blue borders, black status bar |
| `light` | Blue logo, black titles, black borders, white status bar |
| `matrix` | All-green styling on black status bar |

Each theme defines these keys: `logo`, `menu_title`, `menu_border`, `menu_key`, `menu_text`, `panel_border`, `success`, `warning`, `error`, `info`, `dim`, `status_bar`.

### `get_theme(name='default') -> dict`

Returns the theme dictionary for the given name. Falls back to `default` if the name is not recognized.

### `list_themes() -> list`

Returns the list of available theme names: `['default', 'dark', 'light', 'matrix']`.

## Configuration

Theme selection can be stored in `~/.polyterm/config.toml` via the settings screen. The theme name is passed to `get_theme()` at render time.

## Architecture Role

Themes provide a centralized style vocabulary. Menu, logo, status bar, and screen modules can reference theme keys instead of hardcoding colors, enabling consistent appearance changes across the entire TUI.

## Related Modules

- [menu](../infrastructure/menu.md) -- uses theme styles for menu rendering
- [logo](../infrastructure/logo.md) -- uses `logo` style key
- [statusbar](../infrastructure/statusbar.md) -- uses `status_bar` style key

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
