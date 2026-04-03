# Data Export

> Export market data to JSON or CSV files.

## Overview

The Export screen provides a guided wizard for exporting market data to local files. It walks you through selecting a market, choosing a format (JSON or CSV), and specifying an output filename. The exported file is saved to the current working directory by default.

## Access

- **Menu shortcut**: `7` or `e`
- **Menu path**: Page 1 menu item 7

## What It Shows

A step-by-step export flow:

1. Prompts for a market ID or search term
2. Asks for output format (JSON or CSV, defaults to JSON)
3. Asks for output filename (defaults to `export.json` or `export.csv`)
4. Runs the export and displays the absolute path of the saved file

## Navigation / Keyboard Shortcuts

No special keyboard shortcuts. This is a sequential prompt-based flow.

## CLI Command

```bash
polyterm export --market <market> --format json --output export.json
polyterm export --market <market> --format csv --output data.csv
```

## Data Sources

- Gamma REST API for market data
- CLOB API as fallback (via APIAggregator)

## Related Screens

- [History](../screens/history.md) -- view market data before exporting
- [Groups](../screens/groups.md) -- organize markets you may want to export
