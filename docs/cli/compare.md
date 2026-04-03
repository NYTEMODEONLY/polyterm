# Compare

> Compare multiple markets side by side

## Overview

Compare multiple markets side by side. Shows price trends, volumes, and key metrics for easy comparison.

Examples:
polyterm compare -m "bitcoin 100k" -m "bitcoin 90k"
polyterm compare -i   # Interactive mode
polyterm compare -m "trump" -m "biden" --hours 48.

## Usage

### CLI

```bash
polyterm compare [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `cmp`, `compare`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--markets`, `-m` | string | `none` | Market IDs or search terms (can specify multiple) |
| `--hours`, `-h` | int | `24` | Hours of history for comparison (default: 24) |
| `--interactive`, `-i` | flag | `false` | Interactive mode |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Interactive mode
polyterm compare -i

# With hours option
polyterm compare --hours 48

# JSON output
polyterm compare --format json
```

## Data Sources

- Gamma Markets REST API
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Arbitrage](arbitrage.md)
- [Negrisk](negrisk.md)

---

*Source: `polyterm/cli/commands/compare.py`*
