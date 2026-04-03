# Hot

> See what markets are moving right now

## Overview

See what markets are moving right now. Shows the biggest price movers and highest volume markets.

Examples:
polyterm hot                     # Top movers
polyterm hot --gainers           # Only gainers
polyterm hot --losers            # Only losers
polyterm hot --volume            # By volume
polyterm hot -c crypto           # Crypto only.

## Usage

### CLI

```bash
polyterm hot [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `hot`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--limit`, `-l` | int | `15` | Number of markets to show |
| `--category`, `-c` | string | `none` | Filter by category |
| `--gainers`, `-g` | flag | `false` | Show only gainers |
| `--losers` | flag | `false` | Show only losers |
| `--volume`, `-v` | flag | `false` | Sort by volume instead of price change |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm hot

# With limit option
polyterm hot --limit 10

# JSON output
polyterm hot --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Monitor](monitor.md)
- [Live Monitor](live-monitor.md)
- [Watch](watch.md)
- [Search](search.md)
- [Screener](screener.md)

---

*Source: `polyterm/cli/commands/hot.py`*
