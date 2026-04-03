# Glossary

> Prediction market glossary

## Overview

Prediction market glossary. Learn the terminology used in prediction markets and PolyTerm.

Examples:
polyterm glossary                    # View all terms
polyterm glossary --search whale     # Search for "whale"
polyterm glossary --category Trading # View trading terms.

## Usage

### CLI

```bash
polyterm glossary [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `g`, `gloss`, `glossary`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--search`, `-s` | string | `none` | Search for a specific term |
| `--category`, `-c` | string | `none` | Filter by category |
| `--list-categories` | flag | `false` | List all categories |

## Examples

```bash
# Basic usage
polyterm glossary

# List all categories
polyterm glossary --list-categories
```


## Related Commands

- [Dashboard](dashboard.md)
- [Calendar](calendar.md)
- [News](news.md)
- [Leaderboard](leaderboard.md)
- [Health](health.md)

---

*Source: `polyterm/cli/commands/glossary.py`*
