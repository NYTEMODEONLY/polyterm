# Volume

> Analyze volume distribution across price levels

## Overview

Analyze volume distribution across price levels. Shows where trading volume is concentrated to identify
key support/resistance zones and high-activity areas.

Examples:
polyterm volume -m "bitcoin"           # Volume profile
polyterm volume -m "election" -l 15    # More levels.

## Usage

### CLI

```bash
polyterm volume [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `vol`, `volume`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `*required*` | Market to analyze |
| `--levels`, `-l` | int | `10` | Number of price levels |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm volume

# With levels option
polyterm volume --levels 10

# JSON output
polyterm volume --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Monitor](monitor.md)
- [Live Monitor](live-monitor.md)
- [Watch](watch.md)
- [Hot](hot.md)
- [Search](search.md)

---

*Source: `polyterm/cli/commands/volume.py`*
