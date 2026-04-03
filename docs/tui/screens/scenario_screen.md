# Scenario Analysis Screen

> Model what-if outcomes for your positions.

## Overview

The Scenario Analysis screen lets you explore hypothetical outcomes for your portfolio or a specific market. You can see how different resolution scenarios would affect your P&L, helping you plan exit strategies and understand downside risk before committing to positions.

## Access

- **Menu shortcut**: `sc` or `scenario`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A menu with two options:

1. **Analyze portfolio** -- runs scenario analysis across all your positions
2. **Analyze specific market** -- prompts for a market name and models outcomes for that market

## Navigation / Keyboard Shortcuts

- Enter `1` for portfolio analysis, `2` for a specific market
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Portfolio | `polyterm scenario --portfolio` |
| Specific market | `polyterm scenario --market <market>` |

## Data Sources

- Local SQLite database for portfolio positions
- Gamma API for current market data and pricing

## Related Screens

- [Risk Assessment Screen](../screens/risk_screen.md)
- [Exit Plan Screen](../screens/exit.md)
