# Quick Trade Screen

> Analyze trades and get direct Polymarket links.

## Overview

The Quick Trade screen helps you prepare trades by analyzing entry price, shares, fees, and P&L scenarios. It generates a direct link to Polymarket for execution. This screen does not execute trades -- it provides analysis and a convenient link to the Polymarket UI.

## Access

- **Menu shortcut**: `qt` or `quicktrade`
- **Menu path**: Page 2 -> Quick Trade

## What It Shows

A menu with two options:

1. **Interactive trade preparation** -- guided prompts for market, side, and amount
2. **Search for a market** -- enter a market name, side (yes/no), and dollar amount directly

After selection, displays trade analysis including entry price, share count, fee breakdown, breakeven price, and projected P&L.

## Navigation / Keyboard Shortcuts

- Enter `1` for interactive mode, `2` for direct search
- Enter `b` to return to the main menu
- `Ctrl+C` returns to the menu

## CLI Commands

| Option | Command |
|--------|---------|
| Interactive | `polyterm quicktrade -i` |
| Direct | `polyterm quicktrade -m <market> -s <yes/no> -a <amount>` |

## Data Sources

- Gamma API for market data and current pricing
- CLOB API for order book depth and fee calculations

## Related Screens

- [Quick Actions Screen](../screens/quick_screen.md)
- [Fees Screen](../screens/fees.md)
