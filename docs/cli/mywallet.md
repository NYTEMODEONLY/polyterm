# Mywallet

> Connect your wallet and view your Polymarket activity

## Overview

Connect your wallet and view your Polymarket activity. This is a VIEW-ONLY feature - no private keys are stored or needed.
You can track your positions, history, and P&L from your wallet address.

Examples:
polyterm mywallet -c                  # Connect a wallet
polyterm mywallet -p                  # View positions
polyterm mywallet -h                  # View trade history
polyterm mywallet --pnl               # View P&L summary
polyterm mywallet -i                  # Interactive mode
polyterm mywallet -a 0x123...         # View specific wallet.

## Usage

### CLI

```bash
polyterm mywallet [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `mw`, `mywallet`, `wallet`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--address`, `-a` | string | `none` | Wallet address to view |
| `--connect`, `-c` | flag | `false` | Connect/save a wallet address |
| `--disconnect` | flag | `false` | Disconnect saved wallet |
| `--positions`, `-p` | flag | `false` | View open positions |
| `--history`, `-h` | flag | `false` | View trade history |
| `--pnl` | flag | `false` | View P&L summary |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm mywallet -i

# JSON output
polyterm mywallet --format json

# Connect/save a wallet address
polyterm mywallet --connect
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- Local SQLite database (`~/.polyterm/data.db`)
- WebSocket real-time feed
- User configuration (`~/.polyterm/config.toml`)


## Related Commands

- [Portfolio](portfolio.md)
- [Position](position.md)
- [Pnl](pnl.md)
- [Simulate](simulate.md)
- [Parlay](parlay.md)

---

*Source: `polyterm/cli/commands/mywallet.py`*
