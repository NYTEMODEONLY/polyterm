# Watch

> Watch specific markets with customizable alerts

## Overview

Watch specific markets with customizable alerts. The live mode renders a fixed dashboard with current market state, probability/volume changes, check count, and recent alerts while polling continues.

## Usage

### CLI

```bash
polyterm watch [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `4`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market` | string | `*required*` | Market ID or search term |
| `--threshold` | float | `10.0` | Probability change threshold (%) |
| `--volume-threshold` | float | `50.0` | Volume change threshold (%) |
| `--interval` | int | `60` | Check interval in seconds |
| `--notify` | flag | `false` | Enable system notifications |

## Examples

```bash
# Watch a market search term
polyterm watch --market "bitcoin"

# Tighten probability threshold and refresh interval
polyterm watch --market "bitcoin" --threshold 5 --interval 10

# Enable system notifications
polyterm watch --market "bitcoin" --notify
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Monitor](monitor.md)
- [Live Monitor](live-monitor.md)
- [Hot](hot.md)
- [Search](search.md)
- [Screener](screener.md)

---

*Source: `polyterm/cli/commands/watch.py`*
