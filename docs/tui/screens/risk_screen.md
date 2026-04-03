# Risk Assessment Screen

> Evaluate markets on six weighted risk factors with A-F grades.

## Overview

The Risk Assessment screen scores a market across six dimensions: resolution clarity, liquidity quality, time to resolution, volume patterns (wash trading indicators), spread, and category risk. Each market receives a letter grade (A through F) based on a weighted composite score, along with specific warnings and recommendations.

## Access

- **Menu shortcut**: `14` or `risk`
- **Menu path**: Page 2 -> Risk

## What It Shows

After entering a market ID or search term, displays:

- Overall risk grade (A-F) with numeric score
- Breakdown of all six risk factors with individual scores
- Risk warnings for flagged areas
- Actionable recommendations

## Navigation / Keyboard Shortcuts

- Enter a market name or ID when prompted
- Press Enter with no input to return to the menu
- Press Enter after results to return to the menu

## CLI Command

```bash
polyterm risk --market <market>
```

## Data Sources

- Gamma API for market metadata, liquidity, and volume
- Wash trade detection engine for volume quality analysis
- UMA oracle data for resolution clarity assessment

## Related Screens

- [Analyze Screen](../screens/analyze_screen.md)
- [Fees Screen](../screens/fees.md)
