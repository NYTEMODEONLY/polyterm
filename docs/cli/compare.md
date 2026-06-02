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
| `--format` | ['table', 'json'] | `table` | Table view or machine-readable JSON |

## Examples

```bash
# Interactive mode
polyterm compare -i

# With hours option
polyterm compare --hours 48

# JSON output
polyterm compare -m "bitcoin 100k" -m "bitcoin 90k" --format json
```

## Agent Tool

Agents should prefer `market.compare` through MCP or the JSON-lines adapter when they need stable envelope semantics:

```bash
printf '{"tool":"market.compare","args":{"markets":["bitcoin 100k","bitcoin 90k"],"hours":24}}\n' | polyterm agent jsonl-server
```

The agent-native response includes resolved Gamma IDs/slugs, CLOB token IDs, current YES probabilities, recent YES moves, order-book spread context, pairwise probability/liquidity/volume gaps, evidence sources, and quality flags. It is read-only and cannot place trades.

## Data Sources

- Gamma Markets REST API
- CLOB price history and order-book REST APIs for agent-native `market.compare`
- Local SQLite database (`~/.polyterm/data.db`)


## Related Commands

- [Arbitrage](arbitrage.md)
- [Negrisk](negrisk.md)

---

*Source: `polyterm/cli/commands/compare.py`*
