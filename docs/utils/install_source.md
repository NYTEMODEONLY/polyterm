# Install Source -- GitHub-only install and reinstall commands

Constants and helpers that keep install and self-update flows on GitHub `main`. PyPI is decommissioned.

## Overview

PolyTerm is distributed from GitHub. The PyPI project named `polyterm` is decommissioned and is not a delayed mirror of `main`. First-run docs, `install.sh`, TUI update copy, and `polyterm update` must install from the git URL, never from the bare package name `polyterm`.

This module is the single place those GitHub commands are defined so CLI and TUI screens cannot drift back to `pipx install polyterm` or `pip install --upgrade polyterm`.

Source: `polyterm/utils/install_source.py`

## Constants

| Name | Value |
|------|-------|
| `GITHUB_REPO_URL` | `https://github.com/NYTEMODEONLY/polyterm.git` |
| `GITHUB_PIPX_SPEC` | `git+https://github.com/NYTEMODEONLY/polyterm.git@main` |
| `PIPX_FORCE_INSTALL_CMD` | `("pipx", "install", "--force", GITHUB_PIPX_SPEC)` |

`PIPX_FORCE_INSTALL_CMD` is a tuple of argv tokens. The last token is the git spec, not the PyPI package name.

## Functions

### `pip_upgrade_from_github_cmd(python_executable)`

Returns the pip argv that upgrades from GitHub `main`:

```text
<python> -m pip install --upgrade git+https://github.com/NYTEMODEONLY/polyterm.git@main
```

Used when pipx is not available. Callers must pass `sys.executable`.

### `manual_reinstall_commands()`

Returns the two copy-paste strings shown when an automated update fails:

```bash
pipx install --force git+https://github.com/NYTEMODEONLY/polyterm.git@main
pip install --upgrade git+https://github.com/NYTEMODEONLY/polyterm.git@main
```

These strings must not recommend `pipx install polyterm` or `pipx upgrade polyterm`.

### `reinstall_from_github(python_executable, *, runner=subprocess.run)`

Tries pipx first (`pipx install --force <git spec>`), then pip. Does not query `pypi.org`. Returns `(success, method, error_text)`:

| Result | Meaning |
|--------|---------|
| `(True, "pipx", "")` | pipx reinstall from GitHub succeeded |
| `(True, "pip", "")` | pip fallback from GitHub succeeded |
| `(False, "pip", err)` | pipx missed or failed, then pip failed |
| `(False, "", err)` | neither pipx nor pip is available |

`runner` is injectable for tests. Production callers omit it.

## Data Sources

No network APIs. GitHub is the source of truth; this module only builds local installer commands. PyPI JSON (`https://pypi.org/pypi/polyterm/json`) is not used.

## Used By

- `polyterm update` in `polyterm/cli/main.py`
- TUI Settings update (`polyterm/tui/screens/settings.py`)
- TUI menu `quick_update()` (`polyterm/tui/menu.py`)

First-run install paths that must stay aligned, but do not import this module:

- Clone: `git clone https://github.com/NYTEMODEONLY/polyterm.git` then `pip install -e .`
- pipx: `pipx install git+https://github.com/NYTEMODEONLY/polyterm.git@main`
- Script: `install.sh` (same pipx git spec)

## Related Documentation

- [Update command](../cli/update.md)
- [Settings screen](../tui/screens/settings.md)
- [Main menu](../tui/infrastructure/menu.md)
- [Docs index](../README.md)

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm the linked source file still exists and the module name has not changed.
- Keep GitHub `main` as the only advertised install source.
- Do not restore PyPI package-name install commands in first-run or update copy.
- Run `.venv/bin/python scripts/validate_docs.py` before committing documentation changes.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Examples should be copy-pasteable from the repository root unless stated otherwise.
- This helper does not place trades or write wallet keys.
- New modules should have a dedicated page rather than relying only on the index.
