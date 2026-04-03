# News

> View market-relevant news headlines

## Overview

View market-relevant news headlines. Aggregates news from crypto and prediction market RSS feeds.
Optionally filter by market relevance.

Examples:
polyterm news
polyterm news --market "bitcoin"
polyterm news --hours 6 --limit 10
polyterm news --format json.

## Usage

### CLI

```bash
polyterm news [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `nw`, `news`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | `none` | Show news for specific market |
| `--hours` | int | `24` | Hours of news to show (default: 24) |
| `--limit` | int | `20` | Maximum articles to show |
| `--format` | ['table', 'json'] | `table` |  |

## Examples

```bash
# Basic usage
polyterm news

# With hours option
polyterm news --hours 48

# JSON output
polyterm news --format json
```

## Data Sources

- RSS news feeds


## Related Commands

- [Dashboard](dashboard.md)
- [Calendar](calendar.md)
- [Leaderboard](leaderboard.md)
- [Health](health.md)
- [Glossary](glossary.md)

---

*Source: `polyterm/cli/commands/news.py`*
