# Wallets

> Track and analyze whale and smart money wallets

## Overview

Track and analyze whale and smart money wallets.

## Usage

### CLI

```bash
polyterm wallets [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `11`, `wal`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | ['whales', 'smart', 'suspicious', 'all'] | `whales` | Type of wallets to show |
| `--limit` | int | `20` | Maximum wallets to show |
| `--analyze` | string | `none` | Analyze specific wallet address |
| `--track` | string | `none` | Add wallet to tracking list |
| `--untrack` | string | `none` | Remove wallet from tracking list |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Basic usage
polyterm wallets

# With type option
polyterm wallets --type whales

# JSON output
polyterm wallets --format json
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Whales](whales.md)
- [Follow](follow.md)
- [Clusters](clusters.md)
- [Attribution](attribution.md)
- [Groups](groups.md)

---

*Source: `polyterm/cli/commands/wallets.py`*
