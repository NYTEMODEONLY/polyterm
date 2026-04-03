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
