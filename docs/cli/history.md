# History

> CLOB market price history. Refuses instead of inventing a path.

## Overview

`polyterm history` fetches YES prices from CLOB `GET /prices-history` for a Gamma-resolved market. It is view-only: no trades, no private keys.

Without CLOB token IDs or a non-empty history series, the command refuses. It does not synthesize a random walk unless you pass `--demo`, which prints a disclosure first and labels JSON with `uses_historical_data: false`.

Examples:

```bash
polyterm history "bitcoin"
polyterm history "trump" --period month
polyterm history "election" --demo --format json
```

## Usage

### CLI

```bash
polyterm history <market_search> [options]
```

Without CLOB data:

```bash
polyterm history <market_search> --format json
```

returns `success: false`, `source: "none"`, and `uses_historical_data: false`.

### TUI

Shortcuts: `hist`, `history`

The TUI labels the screen as CLOB price history and does not pass `--demo`. If CLOB history is missing, the CLI refusal is shown.

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `market_search` | string | Yes | Gamma search term, slug, or market id |

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--period`, `-p` | ['day', 'week', 'month', 'all'] | `week` | Lookback window |
| `--chart`, `-c` | flag | `false` | ASCII chart (table mode already includes one) |
| `--demo` | flag | `false` | Labeled random-walk series, not CLOB history |
| `--format` | ['table', 'json'] | `table` | Output format |

## Examples

```bash
# Real CLOB history
polyterm history "bitcoin" --period week --format json

# Refuses when CLOB history is missing
polyterm history "bitcoin" --format json

# Labeled demo only
polyterm history "bitcoin" --demo --format json
```

Success JSON includes `uses_historical_data`, `source`, `clob_token_id`, and `history.points`. Demo JSON includes `disclosure` and `source: "demo_random_walk"`.

## How It Works

1. Search Gamma for the market (`search_markets`).
2. Read the primary YES CLOB token ID from `clobTokenIds` (JSON string or list).
3. Call CLOB `GET /prices-history` with `market=<token_id>`, interval/fidelity for the period, and `startTs`/`endTs`.
4. Parse `{t, p}` rows in-window. Empty or failed fetches refuse.
5. Summarize change, high/low, volatility, and trend from those real points.

`--demo` skips CLOB and builds a seeded random walk from the current Gamma YES price only.

## Data Sources

- Gamma Markets REST API for search, title, CLOB token IDs, and current volume snapshot
- CLOB REST `GET /prices-history` (`market` is a CLOB token ID, not a Gamma market id)
- Seeded RNG only with `--demo`

Reported volume is a Gamma snapshot. CLOB history rows do not include volume.

## Related Commands

- [Chart](chart.md) — ASCII chart; also prefers CLOB history
- [Timeline](timeline.md)
- [Replay](replay.md)
- Core helper: [price_history](../core/price_history.md)

---

*Source: `polyterm/cli/commands/history.py`*

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module and command inventory.

When updating this feature:

- Confirm `polyterm/cli/commands/history.py` still exists.
- Keep the refuse-vs-`--demo` contract in CLI, TUI, and JSON examples.
- Do not claim live Polymarket history for the demo path.
- Run `./test_all_commands.sh` and `.venv/bin/python scripts/validate_docs.py`.
