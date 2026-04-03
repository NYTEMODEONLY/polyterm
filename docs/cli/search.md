# Search

> Search markets with advanced filters

## Overview

Search markets with advanced filters. Find markets matching specific criteria for volume, price, liquidity, and more.

Examples:
polyterm search "bitcoin"                          # Basic search
polyterm search --category crypto --min-volume 100000
polyterm search --min-price 60 --max-price 80      # Markets between 60-80%
polyterm search --ending-soon 7                    # Ending within 7 days
polyterm search -i                                 # Interactive mode.

## Usage

### CLI

```bash
polyterm search [query] [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `sr`, `search`

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `query` | string | No | |


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--category`, `-c` | string | `none` | Filter by category (politics, crypto, sports, etc.) |
| `--min-volume`, `-v` | float | `none` | Minimum volume in USD |
| `--max-volume` | float | `none` | Maximum volume in USD |
| `--min-liquidity`, `-l` | float | `none` | Minimum liquidity in USD |
| `--min-price` | float | `none` | Minimum YES price (0-100) |
| `--max-price` | float | `none` | Maximum YES price (0-100) |
| `--ending-soon`, `-e` | int | `none` | Markets ending within N days |
| `--sort`, `-s` | ['volume', 'liquidity', 'price', 'recent'] | `volume` | Sort by |
| `--limit` | int | `20` | Maximum results (default: 20) |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm search <query>

# With sort option
polyterm search <query> --sort volume

# JSON output
polyterm search <query> --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Monitor](monitor.md)
- [Live Monitor](live-monitor.md)
- [Watch](watch.md)
- [Hot](hot.md)
- [Screener](screener.md)

---

*Source: `polyterm/cli/commands/search.py`*
