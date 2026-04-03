# Copy Trading - Wallet Following

> Follow successful traders to learn from their moves.

## Overview

The Follow screen lets you track up to 10 wallet addresses to monitor their trading activity, win rates, and position sizes. This is a view-only feature for learning from other traders -- it does not execute any trades. You can add/remove wallets or use the full interactive mode for deeper analysis.

## Access

- **Menu shortcut**: `15`, `follow`, or `copy`
- **Menu path**: Page 1 menu item 15

## What It Shows

A menu with four options:

1. **List followed wallets** -- shows all wallets you're tracking with stats (win rate, volume, trade count, avg position size)
2. **Follow a new wallet** -- add a wallet address to track (with tips on where to find addresses)
3. **Unfollow a wallet** -- remove a wallet from your list
4. **Interactive mode** -- full-featured wallet following interface

The screen also provides guidance on finding wallet addresses via `polyterm wallets --type smart` and `polyterm wallets --type whales`.

## Navigation / Keyboard Shortcuts

- `1` -- List followed wallets
- `2` -- Follow a new wallet
- `3` -- Unfollow a wallet
- `4` -- Interactive mode (full features)
- `q` -- Return to menu

## CLI Command

```bash
polyterm follow --list           # List followed wallets
polyterm follow --add <address>  # Follow a wallet
polyterm follow --remove <address>  # Unfollow a wallet
polyterm follow                  # Interactive mode
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for followed wallet list
- Data API (`data-api.polymarket.com`) for wallet activity and trade history

## Related Screens

- [Help](../screens/help.md) -- see all wallet-related commands
- [Groups](../screens/groups.md) -- organize followed markets into collections
