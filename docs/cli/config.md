# Config

> Manage PolyTerm configuration

## Overview

Manage PolyTerm configuration.

## Usage

### CLI

```bash
polyterm config [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `8`, `s`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--set` | string | `none` | Set config value (key value) |
| `--get` | string | `none` | Get config value |
| `--list` | flag | `false` | List all configuration |
| `--reset` | flag | `false` | Reset to default configuration |

## Examples

```bash
# Basic usage
polyterm config

# List all configuration
polyterm config --list
```

## Data Sources

- Gamma Markets REST API
- CLOB REST API
- User configuration (`~/.polyterm/config.toml`)


## Related Commands

- [Export](export.md)
- [Update](update.md)
- [Lookup](lookup.md)
- [Timing](timing.md)
- [Similar](similar.md)

---

*Source: `polyterm/cli/commands/config_cmd.py`*
