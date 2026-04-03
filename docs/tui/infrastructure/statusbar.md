# Status Bar

> Status bar display showing connection state, market count, and timestamp.

## Overview

Provides two functions for rendering a bottom status bar with API connection status, tracked market count, and the current time. One function prints directly to a Rich console; the other returns a formatted string for embedding in other layouts.

## Key Classes / Functions

### `display_status_bar(console, market_count=0, connected=True)`

Prints a centered status bar to the console with a blue background. Shows a connection indicator, market count, and `HH:MM:SS` timestamp.

### `create_status_string(connected=True, market_count=0, extra="") -> str`

Returns the same information as a pipe-delimited string without printing. Accepts an optional `extra` parameter appended as an additional segment.

## Configuration

None. All parameters are passed at call time.

## Architecture Role

Used by screens that need to show persistent status information (e.g., live monitors, watch screens). The two-function design allows both direct rendering and integration into Rich `Live` or `Layout` displays.

## Related Modules

- [controller](../infrastructure/controller.md) -- main loop that hosts screens using the status bar
- [themes](../infrastructure/themes.md) -- defines the `status_bar` style key (e.g. `"on blue"`)
