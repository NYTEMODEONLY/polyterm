# Portfolio

> View your Polymarket positions by wallet address.

## Overview

The Portfolio screen displays on-chain positions for a given wallet address. You can enter a wallet address manually or use the one saved in your config file. This is a read-only view -- no private keys are needed.

## Access

- **Menu shortcut**: `6` or `p`
- **Menu path**: Page 1 → Portfolio

## What It Shows

Prompts for a wallet address (or uses the configured default), then displays:

- Current open positions
- Position values and P&L
- Market details for each held position

## Navigation / Keyboard Shortcuts

No special keyboard shortcuts. Enter a wallet address or press Enter to use the configured default. Ctrl+C to stop.

## CLI Command

```bash
polyterm portfolio [--wallet <address>]
```

## Data Sources

- Data API (`data-api.polymarket.com`) for wallet positions
- Gamma REST API for market metadata
- Config file (`~/.polyterm/config.toml`) for default wallet address

## Related Screens

- [My Wallet](../screens/mywallet.md)
- [Position Tracker](../screens/position_screen.md)
- [P&L Tracker](../screens/pnl_screen.md)
