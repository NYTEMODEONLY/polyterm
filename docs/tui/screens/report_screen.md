# Report Screen

> Generate comprehensive trading reports.

## Overview

The Report screen lets you generate different types of summary reports for your trading activity. Reports range from daily market summaries to deep dives on specific markets, giving you a structured view of market conditions and your portfolio performance.

## Access

- **Menu shortcut**: `rp` or `report`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

A menu with four report types:

1. **Daily Report** -- market summary for the day
2. **Weekly Report** -- performance review for the week
3. **Portfolio Report** -- overview of your positions
4. **Market Report** -- deep dive on a specific market (prompts for market name)

## Navigation / Keyboard Shortcuts

- Enter a number `1`-`4` to select a report type
- Enter `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Daily report | `polyterm report -t daily` |
| Weekly report | `polyterm report -t weekly` |
| Portfolio report | `polyterm report -t portfolio` |
| Market report | `polyterm report -t market -m <market>` |

## Data Sources

- Gamma API for market data
- Local SQLite database for portfolio and historical data

## Related Screens

- [Analytics](../screens/analyze_screen.md)
