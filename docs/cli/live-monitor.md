# Live Monitor

> Launch dedicated live market monitor in new terminal window

## Overview

Launch dedicated live market monitor in new terminal window.

## Usage

### CLI

```bash
polyterm live-monitor [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `2`, `l`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market` | string | `none` | Market ID or slug to monitor |
| `--category` | string | `none` | Category to monitor (crypto, politics, sports, etc.) |
| `--interactive` | flag | `false` | Interactive market/category selection |

## Examples

```bash
# Interactive mode
polyterm live-monitor -i

# Interactive market/category selection
polyterm live-monitor --interactive
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed
- User configuration (`~/.polyterm/config.toml`)


## Related Commands

- [Monitor](monitor.md)
- [Watch](watch.md)
- [Hot](hot.md)
- [Search](search.md)
- [Screener](screener.md)

---

*Source: `polyterm/cli/commands/live_monitor.py`*
