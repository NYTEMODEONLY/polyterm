# Clusters Screen

> Detect wallets likely controlled by the same entity.

## Overview

The Clusters screen runs wallet cluster detection to identify groups of wallets that may belong to the same person or organization. It analyzes timing correlation, market overlap, and trade size patterns to produce a confidence score for each detected cluster.

## Access

- **Menu shortcut**: `cl` or `clusters`
- **Menu path**: Type shortcut from either page

## What It Shows

- Detected wallet clusters with confidence scores (0-100)
- Detection signals: timing correlation, market overlap (Jaccard similarity), size patterns
- Risk levels: High (70+), Medium (40-69), Low (0-39)

## Navigation / Keyboard Shortcuts

- **1** - Detect clusters with default settings
- **2** - Detect clusters with a custom minimum score threshold
- **b** - Back to menu
- Ctrl+C returns to menu during execution

## CLI Command

```bash
polyterm clusters
polyterm clusters --min-score <score>
```

## Data Sources

- CLOB API / Gamma API (trade data for wallet analysis)

## Related Screens

- [Whales](../screens/whales_screen.md) - track high-volume wallet activity
- [Copy Trading](../screens/follow_screen.md) - follow specific wallets
