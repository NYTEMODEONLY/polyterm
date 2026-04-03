# Wallet Tracker

> Track and analyze whale, smart money, and suspicious wallets.

## Overview

The Wallet Tracker screen provides a comprehensive interface for monitoring individual wallets on Polymarket. It supports viewing top whale wallets by volume, filtering for smart money (high win rate), identifying suspicious activity, and performing deep analysis on specific wallet addresses.

## Access

- **Menu shortcut**: `11` or `wal`
- **Menu path**: Page 1 → Wallets (option 11)

## What It Shows

A submenu with six operations:

| Option | Description |
|--------|-------------|
| 1 | **Whale Wallets** -- Highest volume traders |
| 2 | **Smart Money** -- High win rate wallets |
| 3 | **Suspicious** -- High insider risk score wallets |
| 4 | **Analyze Wallet** -- Deep dive on a specific address |
| 5 | **Track Wallet** -- Add a wallet to tracking list |
| 6 | **Untrack Wallet** -- Remove from tracking list |

Each viewing option prompts for a result limit (default: 20). Analyze/Track/Untrack prompt for a wallet address.

## Navigation / Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1`-`6` | Select operation |
| `b` | Back to main menu |

## CLI Command

```bash
# View whale wallets
polyterm wallets --type=whales --limit=20

# View smart money wallets
polyterm wallets --type=smart --limit=20

# View suspicious wallets
polyterm wallets --type=suspicious --limit=20

# Analyze a specific wallet
polyterm wallets --analyze=0xABC...

# Track / untrack a wallet
polyterm wallets --track=0xABC...
polyterm wallets --untrack=0xABC...
```

## Data Sources

- Data API (`data-api.polymarket.com`) for wallet positions and trade history
- Gamma REST API for market context
- Local SQLite database for tracked wallet list
- Insider detection scoring from `core/whale_tracker.py`

## Related Screens

- [Whales](../screens/whales.md)
- [Clusters](../screens/alertcenter_screen.md)
- [Copy Trading / Follow](../screens/export.md)
