# Analyze Screen

> Portfolio exposure and risk analysis.

## Overview

The Analyze screen shows portfolio analytics including category exposure, concentration risk, and recommendations for portfolio balance. It launches the CLI command directly without additional prompts.

## Access

- **Menu shortcut**: `an`, `analyze`
- **Menu path**: Extended shortcuts menu

## What It Shows

- Category exposure breakdown
- Concentration risk assessment
- Recommendations for improving portfolio balance

## Navigation / Keyboard Shortcuts

No in-screen navigation. The screen runs the CLI command and returns.

## CLI Command

```
polyterm analyze
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for tracked positions

## Related Screens

- [analytics](../screens/analytics.md) -- market-level analytics (trending, correlations)
- [benchmark_screen](../screens/benchmark_screen.md) -- compare performance to market averages
- [attribution_screen](../screens/attribution_screen.md) -- performance attribution analysis
