# Risk

> Assess risk factors for a market

## Overview

Assess risk factors for a market. Evaluates markets on:
- Resolution clarity (subjective vs objective)
- Liquidity quality
- Time to resolution
- Volume patterns (wash trading indicators)
- Spread
- Category risk

Examples:
polyterm risk --market "bitcoin"
polyterm risk -m 0x1234...

## Usage

### CLI

```bash
polyterm risk [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `14`, `risk`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Market ID or search term |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm risk

# JSON output
polyterm risk --format json
```

## Data Sources

- Gamma Markets REST API
- User configuration (`~/.polyterm/config.toml`)


## Related Commands

- [Config](config.md)
- [Export](export.md)
- [Update](update.md)
- [Lookup](lookup.md)
- [Timing](timing.md)

---

*Source: `polyterm/cli/commands/risk.py`*
