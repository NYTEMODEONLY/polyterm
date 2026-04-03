# Sentiment Screen

> Analyze market sentiment from multiple market signals.

## Overview

The Sentiment screen provides a multi-signal sentiment analysis for a specific market. It combines momentum, volume, order book, trade activity, and whale activity into a composite sentiment view. The user searches for a market by name, and the analysis runs against it.

## Access

- **Menu shortcut**: `sent`, `sentiment`
- **Menu path**: Page 2 (Sentiment)

## What It Shows

After prompting for a market search term, it displays a sentiment analysis that combines:

- Momentum signals
- Volume signals
- Order book analysis
- Trade activity
- Whale activity

## Navigation / Keyboard Shortcuts

No screen-specific shortcuts. The user enters a market search term at the prompt; leaving it blank returns to the menu.

## CLI Command

```bash
polyterm sentiment --market "<search term>"
```

## Data Sources

- Gamma REST API (market data)
- CLOB API (order book, trade activity)

## Related Screens

- [signals_screen](../screens/signals_screen.md) -- entry/exit signals based on multiple factors
- [stats_screen](../screens/stats_screen.md) -- technical indicators and statistics
