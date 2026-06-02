# Update

> Check for and install updates.

## Overview

Check for and install updates.

## Usage

### CLI

```bash
polyterm update [options]
```

### TUI

Not directly accessible from TUI menu. Use the CLI directly.


## Examples

```bash
# Basic usage
polyterm update
```

## Data Sources

- User configuration (`~/.polyterm/config.toml`)
- PyPI API


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
