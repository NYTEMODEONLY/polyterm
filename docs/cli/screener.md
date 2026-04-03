# Screener

> Screen markets by multiple criteria

## Overview

Screen markets by multiple criteria. Filter and find markets matching your specific requirements.
Perfect for finding trading opportunities.

Examples:
polyterm screener -v 10000 -p 0.4           # High volume, mid-price
polyterm screener --ending-within 7         # Resolving soon
polyterm screener --min-change 5            # Big movers
polyterm screener -i                        # Interactive mode.

## Usage

### CLI

```bash
polyterm screener [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `scr`, `screener`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--min-volume`, `-v` | float | `0` | Minimum 24h volume ($) |
| `--max-volume` | float | `none` | Maximum 24h volume ($) |
| `--min-price`, `-p` | float | `0` | Minimum YES price (0-1) |
| `--max-price` | float | `1` | Maximum YES price (0-1) |
| `--min-liquidity`, `-l` | float | `0` | Minimum liquidity ($) |
| `--category`, `-c` | string | `none` | Filter by category |
| `--ending-within`, `-e` | int | `none` | Ending within N days |
| `--min-change` | float | `none` | Minimum 24h change (%) |
| `--max-change` | float | `none` | Maximum 24h change (%) |
| `--sort`, `-s` | ['volume', 'price', 'change', 'liquidity', 'end_date'] | `volume` | Sort results by |
| `--limit` | int | `25` | Maximum results to show |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm screener -i

# With min-volume option
polyterm screener --min-volume 0

# JSON output
polyterm screener --format json
```

## Data Sources

- Gamma Markets REST API


## Related Commands

- [Monitor](monitor.md)
- [Live Monitor](live-monitor.md)
- [Watch](watch.md)
- [Hot](hot.md)
- [Search](search.md)

---

*Source: `polyterm/cli/commands/screener.py`*
