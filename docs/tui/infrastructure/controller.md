# Controller

> Main TUI application loop with screen dispatch and first-run onboarding.

## Overview

`TUIController` is the central coordinator for the PolyTerm TUI. It manages the main event loop: displaying the logo and menu, reading user input, dispatching to the appropriate screen function, and handling quit/interrupt. On first launch, it presents a welcome flow that optionally runs the interactive tutorial.

## Key Classes / Functions

### `TUIController`

The main class that owns the event loop.

| Method | Description |
|--------|-------------|
| `run()` | Main loop -- clears screen, displays logo/menu, dispatches input, shows contextual tips between screens |
| `quit()` | Prints farewell message and sets `self.running = False` |
| `_check_first_run()` | Returns `True` if `~/.polyterm/.onboarded` does not exist |
| `_show_welcome()` | Displays welcome message and optionally launches the tutorial |
| `_mark_onboarded()` | Creates the `~/.polyterm/.onboarded` sentinel file |

### `SCREEN_ROUTES`

A flat dictionary mapping shortcut strings (e.g. `'1'`, `'mon'`, `'arb'`, `'cl'`) to screen functions. Each screen function has the signature `(console: Console) -> None`. This is the single dispatch table for all TUI navigation -- there is no `if/elif` chain.

### `QUIT_COMMANDS`

Set of strings (`'q'`, `'quit'`, `'exit'`) that trigger the quit flow.

## Configuration

- **First-run sentinel**: `~/.polyterm/.onboarded` -- created after the first session. Delete this file to re-trigger the welcome flow.
- **Contextual tips**: After returning from a screen, the controller occasionally displays a random tip via `utils.tips`. Tip context is mapped for a subset of screens (monitor, whales, arbitrage, predictions, orderbook, alerts).

## Architecture Role

`TUIController` is the top-level orchestrator. The CLI entry point (`cli/main.py`) instantiates it and calls `run()` when no subcommand is given. It delegates menu rendering to `MainMenu`, logo display to `display_logo()`, and all feature logic to individual screen functions imported from `tui/screens/`. Pagination signals (`_next_page`, `_prev_page`) from the menu are handled inline by redrawing the logo and continuing the loop.

## Related Modules

- [menu](../infrastructure/menu.md) -- menu display and pagination
- [logo](../infrastructure/logo.md) -- ASCII logo rendering
- [themes](../infrastructure/themes.md) -- color theme definitions
- [shortcuts](../infrastructure/shortcuts.md) -- legacy shortcut mappings

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
