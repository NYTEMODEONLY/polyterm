# Predictions Screen

This page preserves older internal links.

See [predictions](predictions.md) for the screen documentation.

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

## Alias Page Notes

This alias page exists because the source module name and the user-facing command or screen name differ.

Keep the alias when:

- The Python module name uses an implementation suffix such as `_screen`, `_cmd`, or an underscore form.
- The user-facing command uses a shorter name or hyphenated spelling.
- Existing documentation or external links may still reference the module-derived page.
- The docs validator expects a one-to-one source-module mapping.

When editing the canonical page:

- Update this alias if the canonical target changes.
- Keep this page linked from the generated module map when applicable.
- Avoid duplicating the full canonical documentation here.
- Prefer a single source of truth for examples and option tables.
- Re-run the docs validator after changing links.
- Confirm the target file exists in the same docs directory.
- Preserve the source module name in this page title for discoverability.
- Use this page to guide readers to the canonical feature page quickly.
- Keep future module renames backward-compatible where practical.
- Do not turn alias pages into stale copies of command or screen docs.
