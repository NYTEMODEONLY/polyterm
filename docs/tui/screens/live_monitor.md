# Live Monitor Screen

> Real-time market monitoring with WebSocket-powered price updates.

## Overview

The Live Monitor Screen provides an interactive setup flow for launching a real-time market monitor. It supports monitoring a specific market, a category of markets, or all active markets. The monitor launches in a new terminal window (with a fallback to the current terminal) and uses a fixed live dashboard while trades stream.

## Access

- **Menu shortcut**: `2`, `l`
- **Menu path**: Page 1 -> Live Monitor

## What It Shows

A three-step setup flow:

1. **Monitoring mode** -- choose between:
   - Monitor a specific market (search by ID, slug, or keyword)
   - Monitor a category (sports, crypto, politics with sub-categories)
   - Monitor all active markets
2. **Market/category selection** -- depending on mode, search for a market or drill into sub-categories (e.g., Sports -> NFL, Crypto -> Bitcoin)
3. **Launch** -- opens a live monitor in a new terminal window

For category mode, the screen verifies that markets exist for the selected category before launching.

The launched monitor keeps its header, connection state, trade counters, buy/sell totals, last trade time, recent trades table, and status footer visible while CLOB market websocket messages arrive.

## Navigation / Keyboard Shortcuts

- `1`-`3` to select monitoring mode
- Numbered selections for search results and sub-categories
- `Ctrl+C` to cancel setup or stop the monitor

## CLI Command

```bash
polyterm live-monitor [--market <id>] [--category <category>]
```

The screen writes a temporary Python script and launches it in a second terminal, or falls back to the current terminal. The workflow is view-only: it does not place orders. It does write a temp script under the system temp directory.

### Windows second-terminal launch

On `sys.platform == "win32"`, `launch_live_monitor` calls `spawn_windows_live_monitor(sys.executable, script_path)`.

- Interpreter and script path are separate list arguments: `[python_executable, script_path]`
- `shell=False` — no `start`/`cmd` string formatting
- `creationflags=CREATE_NEW_CONSOLE` (win32 only)
- A path with spaces stays one argv element

macOS (`osascript`) and Linux (`gnome-terminal`) launchers are unchanged.

Covered by `tests/test_tui/test_live_monitor_windows_launch.py` (platform patched to `win32`; process launch mocked). A real Windows console cannot be opened on Linux.

## Data Sources

- Gamma REST API (market search, category verification)
- CLOB market WebSocket (`wss://ws-subscriptions-clob.polymarket.com/ws/market`) for real-time trade and price updates
- Polling fallback when WebSocket is unavailable

## Related Screens

- [monitor](../screens/monitor.md) -- polling-based market monitor with category filters
- [market_picker](../screens/market_picker.md) -- reusable market selection component
- [live-monitor CLI](../../cli/live-monitor.md) -- `polyterm live-monitor` command

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

*Source: `polyterm/tui/screens/live_monitor.py`*
