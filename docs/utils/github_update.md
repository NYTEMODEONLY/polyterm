# GitHub Update Check -- compare the install to GitHub tags/releases

Helpers that detect whether NYTEMODEONLY/polyterm has a newer GitHub tag or release than the installed `polyterm.__version__`. PyPI is decommissioned and is not queried.

## Overview

Installed users only see an in-app update when this check finds a newer GitHub version. The TUI main menu calls `newer_github_version()` once per session, caches the result, and shows an update indicator plus an Update row when GitHub is ahead. Install still uses the existing GitHub `main` reinstall path (`reinstall_from_github`).

Network failures, HTTP errors, and unparseable tags return "no update" and never raise. The menu must not crash if GitHub is unreachable.

Source: `polyterm/utils/github_update.py`

## Data Sources

Update availability is checked against GitHub tags/releases, not PyPI.

| Source | URL |
|--------|-----|
| Latest GitHub release | `https://api.github.com/repos/NYTEMODEONLY/polyterm/releases/latest` (`tag_name`) |
| Git tags (fallback) | `https://api.github.com/repos/NYTEMODEONLY/polyterm/tags` (`name`) |

The highest parseable semver wins on the tags fallback. Versions may include a leading `v` (`v0.11.0`); comparison uses `packaging.version` after stripping that prefix.

PyPI JSON (`https://pypi.org/pypi/polyterm/json`) is not used.

## Functions

### `fetch_latest_github_version(*, get_json=None)`

Returns the latest GitHub version string (`"0.11.0"`) or `None` if the check fails. Prefers `/releases/latest`. Falls back to git tags. `get_json` is injectable so tests stub HTTP.

### `newer_github_version(current, *, get_json=None)`

Returns the GitHub version when it is strictly newer than `current`, otherwise `None`. Never raises.

| Installed | GitHub | Result |
|-----------|--------|--------|
| `0.10.0` | `v0.11.0` | `"0.11.0"` |
| `0.11.0` | `v0.11.0` | `None` |
| `0.10.0` | network error | `None` |

## Used By

- TUI `MainMenu.check_for_updates()` (`polyterm/tui/menu.py`) -- caches the result for the menu session
- Menu Update row (`u`), Settings option `6`, and `polyterm update` install via `reinstall_from_github` (GitHub `main`)

This module only reports availability. It does not install packages or write wallet keys.

## Related Documentation

- [Install source](install_source.md)
- [Update command](../cli/update.md)
- [Main menu](../tui/infrastructure/menu.md)
- [Settings screen](../tui/screens/settings.md)
- [Docs index](../README.md)

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm the linked source file still exists and the module name has not changed.
- Keep GitHub tags/releases as the check source. Do not restore PyPI version queries.
- Run `.venv/bin/python scripts/validate_docs.py` before committing documentation changes.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Examples should be copy-pasteable from the repository root unless stated otherwise.
- This helper does not place trades or write wallet keys.
- New modules should have a dedicated page rather than relying only on the index.
