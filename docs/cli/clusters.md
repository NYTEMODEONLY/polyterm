# Clusters

> Detect wallet clusters (same entity controlling multiple wallets)

## Overview

Detect wallet clusters (same entity controlling multiple wallets). Analyzes trading patterns to identify wallets that may be controlled
by the same person or entity. Checks timing correlation, market overlap,
and position size patterns.

Examples:
polyterm clusters
polyterm clusters --min-score 70
polyterm clusters --format json.

## Usage

### CLI

```bash
polyterm clusters [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `cl`, `clusters`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--min-score` | int | `60` | Minimum cluster score (0-100) |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm clusters

# With min-score option
polyterm clusters --min-score 60

# JSON output
polyterm clusters --format json
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Whales](whales.md)
- [Follow](follow.md)
- [Wallets](wallets.md)
- [Attribution](attribution.md)
- [Groups](groups.md)

---

*Source: `polyterm/cli/commands/clusters.py`*
