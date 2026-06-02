# Collect

> Research archive snapshot collection for Polymarket markets.

## Overview

`polyterm collect` records repeatable market snapshots into PolyTerm's local SQLite database. It is for data collectors, researchers, and agents that need a durable local record rather than only live terminal output.

The command is foreground-only. It does not create a daemon and does not mutate external Polymarket state. It only writes local archive snapshots.

## Usage

### CLI

```bash
polyterm collect --market "bitcoin"
polyterm collect --market "bitcoin" --interval 30s --duration 10m
polyterm collect --market "bitcoin" --format json
```

### TUI

There is no TUI screen yet. Collection is a command-line workflow because it may run for a fixed foreground duration.

## Options / Parameters

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market`, `-m` | string | required | Market slug, ID, or search term. |
| `--interval` | duration | `30s` | Time between snapshots during duration mode. |
| `--duration` | duration | `0s` | Total foreground collection duration. `0s` collects once. |
| `--format` | choice | `table` | Use `json` for agent and script output. |

## Examples

```bash
# Collect one snapshot
polyterm collect -m bitcoin

# Collect for ten minutes
polyterm collect -m bitcoin --interval 30s --duration 10m

# Agent-safe output
polyterm collect -m bitcoin --format json
```

## How It Works

The command uses `ArchiveCollector` from `polyterm/core/archive.py`. The collector resolves the market through Gamma, normalizes the probability through `market_utils`, creates a `MarketSnapshot`, and inserts it through the existing database manager.

Duration mode loops in the foreground and sleeps between snapshots. Ctrl+C stops collection without corrupting existing records.

## Data Sources

- Gamma API for market metadata and current probability fields.
- Local SQLite table `market_snapshots` for persisted archive rows.

## Agent Workflow

Agents should use `collect` when a market needs local observation before a thesis, export, replay, or alert workflow. Dataset manifests can then be requested with `polyterm export --dataset latest --format json`.

## Verification

```bash
polyterm collect -m bitcoin --format json
polyterm export --dataset latest --format json
```

Run `scripts/validate_docs.py` and command smoke after adding archive features.

## Related Features

- [Export](export.md)
- [Replay](replay.md)
- [Archive Core](../core/archive.md)
- [Agent](agent.md)
