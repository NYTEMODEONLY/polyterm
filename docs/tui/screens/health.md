# Portfolio Health Check

> Comprehensive portfolio health analysis with grades.

## Overview

The Health screen analyzes your tracked portfolio and provides a health score with grades. It evaluates diversification, risk exposure, position concentration, and other factors to give you an overall assessment of your portfolio's condition. Available as a quick check or a detailed deep-dive.

## Access

- **Menu shortcut**: `hp` or `health`
- **Menu path**: Page 2 extended shortcuts

## What It Shows

A menu with two analysis levels:

1. **Quick health check** -- summary health score and key metrics
2. **Detailed analysis** -- in-depth breakdown of all health factors

## Navigation / Keyboard Shortcuts

- `1` -- Quick health check
- `2` -- Detailed analysis
- `b` -- Back to main menu

## CLI Command

```bash
polyterm health              # Quick health check
polyterm health --detailed   # Detailed analysis
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) for tracked positions
- Gamma API for current market data

## Related Screens

- [Exit Strategy](../screens/exit.md) -- plan exits for unhealthy positions
- [Fees](../screens/fees.md) -- understand cost drag on portfolio health
