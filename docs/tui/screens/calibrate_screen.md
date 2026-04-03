# Calibrate Screen

> Track and measure the accuracy of your probability estimates.

## Overview

The Calibrate screen helps you improve as a forecaster by logging probability predictions, resolving them when outcomes are known, and viewing calibration statistics that show how well your estimates match reality.

## Access

- **Menu shortcut**: `cb`, `calibrate`
- **Menu path**: Extended shortcuts menu

## What It Shows

A four-option menu:

1. **View calibration stats** -- how accurate your predictions have been
2. **Log a new prediction** -- record a probability estimate for a market
3. **Resolve a prediction** -- mark a prediction as correct or incorrect
4. **List all predictions** -- view all logged predictions

## Navigation / Keyboard Shortcuts

- `1`-`4` to select an option
- `b` to return to the main menu

## CLI Commands

| Option | Command |
|--------|---------|
| Stats | `polyterm calibrate --stats` |
| Add prediction | `polyterm calibrate --add` |
| Resolve | `polyterm calibrate --resolve` |
| List all | `polyterm calibrate --list` |

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)

## Related Screens

- [attribution_screen](../screens/attribution_screen.md) -- performance attribution
- [benchmark_screen](../screens/benchmark_screen.md) -- performance benchmarking
