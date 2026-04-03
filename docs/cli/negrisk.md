# Negrisk

> Scan multi-outcome markets for NegRisk arbitrage

## Overview

Scan multi-outcome markets for NegRisk arbitrage. Finds markets where the sum of all YES outcome prices doesn't equal $1.00.
If total < $1.00, buying all outcomes guarantees profit on resolution.

Examples:
polyterm negrisk
polyterm negrisk --min-spread 0.03
polyterm negrisk --format json.

## Usage

### CLI

```bash
polyterm negrisk [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `nr`, `negrisk`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--min-spread` | float | `0.02` | Minimum spread threshold (default: 0.02) |
| `--limit` | int | `20` | Maximum opportunities to show |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm negrisk

# With min-spread option
polyterm negrisk --min-spread 0.03

# JSON output
polyterm negrisk --format json
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API


## Related Commands

- [Arbitrage](arbitrage.md)
- [Compare](compare.md)

---

*Source: `polyterm/cli/commands/negrisk.py`*
