# Follow

> Manage followed wallets for copy trading

## Overview

Manage followed wallets for copy trading. Follow successful traders to see their moves and learn from their strategies.

Examples:
polyterm follow --list                    # List followed wallets
polyterm follow --add 0x1234...           # Follow a wallet
polyterm follow --remove 0x1234...        # Unfollow a wallet.

## Usage

### CLI

```bash
polyterm follow [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `15`, `follow`, `copy`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--add`, `-a` | string | `none` | Follow a wallet address |
| `--remove`, `-r` | string | `none` | Unfollow a wallet address |
| `--list` | flag | `false` | List followed wallets |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm follow

# JSON output
polyterm follow --format json

# List followed wallets
polyterm follow --list
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Whales](whales.md)
- [Wallets](wallets.md)
- [Clusters](clusters.md)
- [Attribution](attribution.md)
- [Groups](groups.md)

---

*Source: `polyterm/cli/commands/follow.py`*
