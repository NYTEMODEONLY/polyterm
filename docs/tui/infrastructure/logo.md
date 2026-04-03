# Logo

> Responsive ASCII logo display for the TUI header.

## Overview

Renders the PolyTerm ASCII art logo at the top of the terminal, adapting to the current terminal width. Three size variants ensure the logo fits terminals from narrow (< 60 columns) to wide (>= 80 columns). The logo is displayed on every menu refresh cycle.

## Key Classes / Functions

### `display_logo(console: Console)`

Detects terminal width via `console.size.width` (respects `COLUMNS` env var override) and prints the appropriate logo variant:

| Width | Variant | Content |
|-------|---------|---------|
| >= 80 | Full | Complete "POLYTERM" block letters + tagline |
| >= 60 | Medium | Same block letters, reduced left padding |
| < 60 | Compact | Truncated "POLYT" block letters + short tagline |

All variants are styled `bold cyan` and followed by a `bright_magenta` "a nytemode project" attribution line.

## Configuration

- **`COLUMNS` environment variable**: If set, overrides `console.size.width` for logo size selection. Useful for testing specific terminal widths.

## Architecture Role

Called by `TUIController.run()` at startup and after every screen return to re-render the header. It is a stateless display function with no side effects beyond console output.

## Related Modules

- [controller](../infrastructure/controller.md) -- calls `display_logo()` in the main loop
- [themes](../infrastructure/themes.md) -- defines the `logo` style key (though the current implementation hardcodes `bold cyan`)
