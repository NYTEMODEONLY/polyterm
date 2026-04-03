# Replay

> Replay historical market data

## Overview

Replay historical market data.

## Usage

### CLI

```bash
polyterm replay [options]
```

### TUI

Not directly accessible from TUI menu. Use the CLI directly.


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market` | string | `*required*` | Market ID or search term |
| `--hours` | int | `24` | Hours of history to show |
| `--speed` | float | `1.0` | Playback speed multiplier |
| `--trades` | flag | `false` | Show individual trades |

## Examples

```bash
# Basic usage
polyterm replay

# With hours option
polyterm replay --hours 48

# Show individual trades
polyterm replay --trades
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Chart](chart.md)
- [Timeline](timeline.md)
- [History](history.md)
- [Recent](recent.md)
- [Streak](streak.md)

---

*Source: `polyterm/cli/commands/replay.py`*
