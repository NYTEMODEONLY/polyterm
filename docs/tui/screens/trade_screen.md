# Quick Trade Calculator

> Analyze fees, slippage, breakeven, and profit scenarios before trading.

## Overview

The Quick Trade Calculator provides a comprehensive pre-trade analysis for any market. It calculates fees, slippage estimates, breakeven price, and profit/loss scenarios so you can evaluate a trade before executing it. This screen does not execute trades -- it provides analysis only.

## Access

- **Menu shortcut**: `tr` or `trade`
- **Menu path**: Page 2 → Quick Trade Calculator

## What It Shows

- Entry price and share count
- Dynamic CLOB V2 protocol fee estimate
- Slippage estimate from order book
- Breakeven price
- Profit if win / loss if lose scenarios
- Risk/reward ratio

## Navigation / Keyboard Shortcuts

The screen prompts sequentially for:

1. Market search term
2. Side (`yes` or `no`)
3. Trade amount in dollars (default: $100)

## CLI Command

```bash
polyterm trade --market "bitcoin" --side yes --amount 100
```

## Data Sources

- Gamma REST API for market data
- CLOB API for order book depth and slippage estimation

## Related Screens

- [Fees Calculator](../screens/exit.md)
- [Position Size Calculator](../screens/analyze_screen.md)
