# Crypto 15M Screen

> Monitor and trade short-term crypto price prediction markets that resolve every 15 minutes.

## Overview

The Crypto 15M screen provides access to Polymarket's short-term cryptocurrency prediction markets for BTC, ETH, SOL, and XRP. These markets resolve every 15 minutes based on Chainlink oracle price feeds, predicting whether the price will go UP or DOWN in the next interval.

## Access

- **Menu shortcut**: `c15`, `crypto15m`, or `15m`
- **Menu path**: Page 2 (listed as "15M Crypto")

## What It Shows

- Current 15-minute crypto prediction markets
- Prices and odds for each crypto asset
- Resolution countdown timers
- Trade analysis in interactive mode

## Navigation / Keyboard Shortcuts

- **1** - Monitor all 15M markets (BTC, ETH, SOL, XRP)
- **2** - Monitor Bitcoin (BTC) only
- **3** - Monitor Ethereum (ETH) only
- **4** - Monitor Solana (SOL) only
- **5** - Monitor XRP only
- **6** - Interactive mode (analyze and trade)
- **b** - Back to menu
- Ctrl+C returns to menu during monitoring

## CLI Command

```bash
polyterm crypto15m                # All assets
polyterm crypto15m -c BTC         # Bitcoin only
polyterm crypto15m -c ETH         # Ethereum only
polyterm crypto15m -c SOL         # Solana only
polyterm crypto15m -c XRP         # XRP only
polyterm crypto15m -i             # Interactive mode
```

## Data Sources

- Gamma REST API (market listings and pricing)
- Chainlink oracle price feeds (resolution source)

## Related Screens

- [Dashboard](../screens/dashboard_screen.md) - quick overview including market activity
- [Chart](../screens/chart_screen.md) - price history for crypto markets
