# Odds Converter

> Convert between probability, decimal odds, and American odds formats.

## Overview

The Odds screen converts betting odds between different formats commonly used in prediction markets and sports betting. It can also look up the current odds for a specific Polymarket market. Useful when comparing Polymarket probabilities with traditional betting platforms.

## Access

- **Menu shortcut**: `od` or `odds`
- **Menu path**: Page 2 → Odds

## What It Shows

A menu with five conversion options:

1. **Convert probability** -- input a decimal probability (e.g., 0.65) to see all formats
2. **Convert decimal odds** -- input decimal odds (e.g., 2.5)
3. **Convert American odds** -- input American odds (e.g., +150)
4. **Get odds from market** -- look up a market by name and display its odds
5. **Interactive mode** -- guided conversion workflow

## Navigation / Keyboard Shortcuts

Standard numbered menu (`1`-`5`, `b` to go back).

## CLI Commands

| Option | CLI command |
|--------|-------------|
| From probability | `polyterm odds <value>` |
| From decimal | `polyterm odds <value> --from decimal` |
| From American | `polyterm odds <value> --from american` |
| From market | `polyterm odds --market <name>` |
| Interactive | `polyterm odds -i` |

## Data Sources

- Pure calculation (no API needed) for format conversion
- Gamma REST API for market lookups

## Related Screens

- [Predictions](../screens/predictions.md)
- [Parlay Calculator](../screens/parlay_screen.md)
