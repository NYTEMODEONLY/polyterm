# Crypto15M

> Monitor 15-minute crypto prediction markets (BTC, ETH, SOL, XRP)

## Overview

Monitor 15-minute crypto prediction markets (BTC, ETH, SOL, XRP). These markets resolve every 15 minutes based on whether the crypto price
goes UP or DOWN. Resolution uses Chainlink price feeds.

Note: 15M markets may not always be available via API. Use --links to get
direct Polymarket URLs for live 15M trading.

Examples:
polyterm crypto15m                    # Monitor all 15M crypto markets
polyterm crypto15m -c BTC             # Monitor Bitcoin 15M only
polyterm crypto15m -c ETH --refresh 3 # Ethereum with 3s refresh
polyterm crypto15m -i                 # Interactive mode
polyterm crypto15m --links            # Show direct Polymarket links.

## Usage

### CLI

```bash
polyterm crypto15m [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `c15`, `crypto15m`, `15m`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--crypto`, `-c` | ['BTC', 'ETH', 'SOL', 'XRP', 'all'] | `all` | Cryptocurrency to monitor |
| `--refresh`, `-r` | int | `5` | Refresh interval in seconds |
| `--interactive`, `-i` | flag | `false` | Interactive mode with trade analysis |
| `--format` | ['table', 'json'] | `table` |  |
| `--once` | flag | `false` | Run once and exit (no live updates) |
| `--links`, `-l` | flag | `false` | Show direct Polymarket links |

## Examples

```bash
# Interactive mode
polyterm crypto15m -i

# With crypto option
polyterm crypto15m --crypto all

# JSON output
polyterm crypto15m --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


---

*Source: `polyterm/cli/commands/crypto15m.py`*
