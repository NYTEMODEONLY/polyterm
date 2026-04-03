# Groups

> Organize markets into named watchlist groups

## Overview

Organize markets into named watchlist groups. Create collections of related markets for easy tracking.

Examples:
polyterm groups --list                           # List all groups
polyterm groups --create "crypto"                # Create new group
polyterm groups --view "crypto"                  # View group markets
polyterm groups --add "crypto" -m "bitcoin"      # Add market to group
polyterm groups --remove "crypto" -m "bitcoin"   # Remove from group
polyterm groups --delete "crypto"                # Delete group.

## Usage

### CLI

```bash
polyterm groups [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `gr`, `groups`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--list`, `-l` | flag | `false` | List all groups |
| `--create`, `-c` | string | `none` | Create new group |
| `--view`, `-v` | string | `none` | View group markets |
| `--add`, `-a` | string | `none` | Add market to group |
| `--remove`, `-r` | string | `none` | Remove market from group |
| `--delete`, `-d` | string | `none` | Delete a group |
| `--market`, `-m` | string | `none` | Market to add/remove |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm groups

# JSON output
polyterm groups --format json

# List all groups
polyterm groups --list
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Whales](whales.md)
- [Follow](follow.md)
- [Wallets](wallets.md)
- [Clusters](clusters.md)
- [Attribution](attribution.md)

---

*Source: `polyterm/cli/commands/groups.py`*
