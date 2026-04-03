# Monitor

> Monitor markets in real-time with live updates

## Overview

Monitor markets in real-time with live updates.

## Usage

### CLI

```bash
polyterm monitor [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `1`, `mon`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--limit` | int | `20` | Maximum number of markets to display |
| `--category` | string | `none` | Filter by category (politics, crypto, sports) |
| `--refresh` | int | `5` | Refresh interval in seconds |
| `--active-only` | flag | `false` | Show only active markets |
| `--sort` | ['volume', 'probability', 'recent'] | `none` | Sort markets by: volume, probability, or recent |
| `--format` | ['table', 'json'] | `table` | Output format: table (default) or json |
| `--once` | flag | `false` | Run once and exit (no live updates) |
| `--show-quality` | flag | `false` | Show volume quality indicators (wash trade detection) |

## Examples

```bash
# Basic usage
polyterm monitor

# With limit option
polyterm monitor --limit 10

# JSON output
polyterm monitor --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Live Monitor](live-monitor.md)
- [Watch](watch.md)
- [Hot](hot.md)
- [Search](search.md)
- [Screener](screener.md)

---

*Source: `polyterm/cli/commands/monitor.py`*
