# Portfolio

> View portfolio and positions

## Overview

View portfolio and positions.

## Usage

### CLI

```bash
polyterm portfolio [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `6`, `p`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--wallet` | string | `none` | Wallet address (or use config) |

## Examples

```bash
# Basic usage
polyterm portfolio
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- WebSocket real-time feed


## Related Commands

- [Position](position.md)
- [Pnl](pnl.md)
- [Simulate](simulate.md)
- [Parlay](parlay.md)
- [Exit](exit.md)

---

*Source: `polyterm/cli/commands/portfolio.py`*
