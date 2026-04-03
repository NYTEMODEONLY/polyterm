# Rewards

> View estimated holding and liquidity rewards

## Overview

View estimated holding and liquidity rewards. Estimates your 4% APY holding rewards based on qualifying positions.
Qualifying positions must be priced between 20-80 cents and held 24+ hours.

Examples:
polyterm rewards
polyterm rewards --wallet 0x123...
polyterm rewards --format json.

## Usage

### CLI

```bash
polyterm rewards [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `rw`, `rewards`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--wallet`, `-w` | string | `none` | Wallet address to check |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm rewards

# JSON output
polyterm rewards --format json
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Portfolio](portfolio.md)
- [Position](position.md)
- [Pnl](pnl.md)
- [Simulate](simulate.md)
- [Parlay](parlay.md)

---

*Source: `polyterm/cli/commands/rewards.py`*
