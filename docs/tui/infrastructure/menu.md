# Menu

> Paginated main menu display with version checking and self-update capability.

## Overview

`MainMenu` renders the two-page TUI main menu using Rich tables, checks PyPI for newer versions (once per session), and provides a `quick_update()` method that can upgrade PolyTerm in-place and restart the process. It handles pagination navigation internally and returns either the user's choice or a pagination signal to the controller.

## Key Classes / Functions

### `MainMenu`

| Method | Description |
|--------|-------------|
| `display()` | Renders the current menu page as a Rich grid with key, name, and description columns. Shows version string and update indicator. |
| `get_choice()` | Reads user input. Returns the choice string, or `"_next_page"` / `"_prev_page"` for pagination keys (`m`/`more`/`+`/`next` and `b`/`back`/`-`/`prev`). |
| `reset_page()` | Resets `current_page` to 1. Called by the controller after each screen returns. |
| `check_for_updates()` | Queries `pypi.org/pypi/polyterm/json` (5s timeout). Returns `(indicator_string, latest_version)`. Result is cached for the session in `_update_cache`. |
| `quick_update()` | Attempts upgrade via `pipx upgrade`, falling back to `pipx uninstall`+`install`, then `pip install --upgrade`. On success, offers to restart via `os.execv`. |

### Menu Pages

- **Page 1** -- Core features: Monitor, Live Monitor, Whales, Watch, Analytics, Portfolio, Export, Settings, Dashboard, Tutorial, Help, Quit. If an update is available, an "Update" row is inserted.
- **Page 2** -- Advanced features: Arbitrage, Predictions, Wallets, Alerts, Order Book, Risk, Copy Trading, Parlay, Bookmarks, 15M Crypto, My Wallet, Quick Trade, Glossary, Simulate.

## Configuration

No config file options. Update checking uses `polyterm.__version__` and the PyPI JSON API. The `_update_cache` attribute ensures only one HTTP request per session.

## Architecture Role

`MainMenu` is instantiated by `TUIController` and called each iteration of the main loop. It is purely a display and input component -- it does not dispatch to screens. The controller reads the return value from `get_choice()` and handles routing via `SCREEN_ROUTES`.

## Related Modules

- [controller](../infrastructure/controller.md) -- owns the `MainMenu` instance and consumes its output
- [logo](../infrastructure/logo.md) -- displayed above the menu
- [statusbar](../infrastructure/statusbar.md) -- status display utilities
