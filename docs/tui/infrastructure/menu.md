# Menu

> Paginated main menu display with version checking and self-update capability.

## Overview

`MainMenu` renders the two-page TUI main menu using Rich tables and provides a `quick_update()` method that reinstalls PolyTerm from GitHub `main` (same path as Settings). Update availability is checked against GitHub tags/releases, not PyPI. It handles pagination navigation internally and returns either the user's choice or a pagination signal to the controller.

## Key Classes / Functions

### `MainMenu`

| Method | Description |
|--------|-------------|
| `display()` | Renders the current menu page as a Rich grid with key, name, and description columns. Shows version string and update indicator. |
| `get_choice()` | Reads user input. Returns the choice string, or `"_next_page"` / `"_prev_page"` for pagination keys (`m`/`more`/`+`/`next` and `b`/`back`/`-`/`prev`). |
| `reset_page()` | Resets `current_page` to 1. Called by the controller after each screen returns. |
| `check_for_updates()` | Compares `polyterm.__version__` to GitHub tags/releases (NYTEMODEONLY/polyterm). Cached for the menu session. On a newer tag, returns an update indicator and version so the menu shows `u 🔄 Update`. Network failure returns empty strings and does not crash the menu. Does not query PyPI. |
| `quick_update()` | Delegates to Settings `update_polyterm()`, which reinstalls from GitHub `main` via `pipx install --force git+https://github.com/NYTEMODEONLY/polyterm.git@main` (pip fallback). On success, offers to restart via `os.execv`. |

### Menu Pages

- **Page 1** -- Core features: Monitor, Live Monitor, Whales, Watch, Analytics, Portfolio, Export, Settings, Dashboard, Tutorial, Help, Quit. If an update is available, an "Update" row is inserted.
- **Page 2** -- Advanced features: Arbitrage, Predictions, Wallets, Alerts, Order Book, Risk, Copy Trading, Parlay, Bookmarks, 15M Crypto, My Wallet, Quick Trade, Glossary, Simulate.

## Configuration

No config file options. The menu checks GitHub tags/releases once per session. Reinstall from GitHub `main` with Settings option `6`, menu shortcut `u`, or `polyterm update`.

## Architecture Role

`MainMenu` is instantiated by `TUIController` and called each iteration of the main loop. It is purely a display and input component -- it does not dispatch to screens. The controller reads the return value from `get_choice()` and handles routing via `SCREEN_ROUTES`.

## Related Modules

- [controller](../infrastructure/controller.md) -- owns the `MainMenu` instance and consumes its output
- [logo](../infrastructure/logo.md) -- displayed above the menu
- [statusbar](../infrastructure/statusbar.md) -- status display utilities
- [GitHub update check](../../utils/github_update.md) -- GitHub tags/releases compared to the installed version

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
