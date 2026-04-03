# Shortcuts

> Keyboard shortcut mappings for TUI menu navigation.

## Overview

This module defines a static `SHORTCUTS` dictionary that maps key strings to action names, plus a `get_action()` lookup helper. It represents an earlier, simpler shortcut system. The authoritative dispatch table used at runtime is `SCREEN_ROUTES` in `controller.py`, which maps directly to screen functions and covers far more entries.

## Key Classes / Functions

### `SHORTCUTS`

A dictionary mapping single characters and words to action name strings:

- Number keys `'1'`-`'7'` map to core screens (monitor, whales, watch, analytics, portfolio, export, settings).
- Letter shortcuts `'m'`, `'w'`, `'a'`, `'p'`, `'e'`, `'s'` duplicate the number mappings.
- `'h'`, `'?'` map to `'help'`; `'q'`, `'exit'`, `'quit'` map to `'quit'`.

### `get_action(key: str) -> str`

Looks up a key in `SHORTCUTS`. Returns the mapped action name, or the original key unchanged if no mapping exists.

## Configuration

None. The mappings are hardcoded.

## Architecture Role

This module is a legacy utility. The controller's `SCREEN_ROUTES` dictionary has superseded it for actual screen dispatch, but `shortcuts.py` remains available for any code that needs to resolve a key press to a logical action name.

## Related Modules

- [controller](../infrastructure/controller.md) -- `SCREEN_ROUTES` is the active dispatch table
- [menu](../infrastructure/menu.md) -- handles pagination shortcuts (`m`, `b`) directly
