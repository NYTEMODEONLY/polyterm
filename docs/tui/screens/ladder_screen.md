# Ladder Screen

> Visual order book depth at each price level for a market.

## Overview

The Ladder Screen displays a price ladder view of the order book for a given market. It shows liquidity at each price level and lets you choose whether to view the YES side, NO side, or both.

## Access

- **Menu shortcut**: `lad`, `ladder`
- **Menu path**: Extended shortcuts menu

## What It Shows

A price ladder visualization showing order book depth at each price level for the selected market. The user is prompted for:

1. **Market** -- enter a market name or identifier
2. **Side** -- choose YES only, NO only, or both sides

## Navigation / Keyboard Shortcuts

- Select side: `1` (Both), `2` (YES only), `3` (NO only)

## CLI Commands

| Option | Command |
|--------|---------|
| Both sides | `polyterm ladder <market> --side both` |
| YES only | `polyterm ladder <market> --side yes` |
| NO only | `polyterm ladder <market> --side no` |

## Data Sources

- CLOB API (order book data)

## Related Screens

- [orderbook_screen](../screens/orderbook_screen.md) -- real-time order book with live WebSocket feed
- [liquidity_screen](../screens/liquidity_screen.md) -- compare liquidity across markets
