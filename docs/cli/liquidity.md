# Liquidity

> Compare liquidity across markets

## Overview

Compare liquidity across markets. Find the most liquid markets for easier trading with
lower slippage and better execution.

Metrics:
liquidity - Total order book depth
spread    - Bid-ask spread (lower is better)
depth     - Combined bid/ask size
score     - Composite liquidity score

Examples:
polyterm liquidity                    # Top liquid markets
polyterm liquidity -c "crypto"        # Crypto markets only
polyterm liquidity -s spread          # Sort by tightest spread
polyterm liquidity -v 10000           # High volume only.

## Usage

### CLI

```bash
polyterm liquidity [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `liq`, `liquidity`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--category`, `-c` | string | `none` | Filter by category |
| `--min-volume`, `-v` | float | `1000` | Minimum 24h volume |
| `--limit`, `-l` | int | `20` | Number of markets to compare |
| `--sort`, `-s` | ['liquidity', 'spread', 'depth', 'score'] | `score` | Sort by metric |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm liquidity

# With min-volume option
polyterm liquidity --min-volume 1000

# JSON output
polyterm liquidity --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Config](config.md)
- [Export](export.md)
- [Update](update.md)
- [Lookup](lookup.md)
- [Timing](timing.md)

---

*Source: `polyterm/cli/commands/liquidity.py`*
