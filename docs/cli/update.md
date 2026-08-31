# Update

> Reinstall PolyTerm from GitHub main. PyPI is decommissioned.

## Overview

`polyterm update` reinstalls the current machine from GitHub `main`. GitHub is the source of truth. It does not query PyPI and does not install the PyPI package name `polyterm`.

The command prefers `pipx install --force git+https://github.com/NYTEMODEONLY/polyterm.git@main`, then falls back to `pip install --upgrade` with the same git spec. After a successful reinstall, restart PolyTerm to load the new code.

This command mutates the local install. It does not place trades or write wallet keys.

## Usage

### CLI

```bash
polyterm update
```

Confirm the prompt to reinstall from GitHub `main`.

### TUI

- Settings screen option `6` (`8` or `s` from the main menu, then `6`)
- Main-menu shortcut `u` / `update` (same GitHub reinstall as Settings)

## Examples

```bash
# Reinstall from GitHub main
polyterm update
```

Manual equivalent when the command cannot run pipx or pip:

```bash
pipx install --force git+https://github.com/NYTEMODEONLY/polyterm.git@main
pip install --upgrade git+https://github.com/NYTEMODEONLY/polyterm.git@main
```

## Data Sources

- Installed package version (`polyterm.__version__`)
- GitHub `main` via pipx or pip (`git+https://github.com/NYTEMODEONLY/polyterm.git@main`)

PyPI is decommissioned and is not consulted.


## Related Commands

- [Config](config.md)
- [Export](export.md)
- [Lookup](lookup.md)
- [Timing](timing.md)
- [Similar](similar.md)

---

*Source: `polyterm/cli/main.py`*

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
