# Attribution

> Analyze what's driving your trading performance

## Overview

Analyze what's driving your trading performance. Breaks down P&L by:
- Category (crypto, politics, sports, etc.)
- Side (YES vs NO positions)
- Position size (small, medium, large)
- Hold time (quick trades vs long holds)

Examples:
polyterm attribution                   # Last month
polyterm attribution --period quarter  # Last quarter
polyterm attribution --period all      # All time.

## Usage

### CLI

```bash
polyterm attribution [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `attr`, `attribution`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--period`, `-p` | ['week', 'month', 'quarter', 'year', 'all'] | `month` | Time period |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm attribution

# With period option
polyterm attribution --period month

# JSON output
polyterm attribution --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Whales](whales.md)
- [Follow](follow.md)
- [Wallets](wallets.md)
- [Clusters](clusters.md)
- [Groups](groups.md)

---

*Source: `polyterm/cli/commands/attribution.py`*
