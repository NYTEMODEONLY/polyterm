# Portfolio

> View portfolio and positions

## Overview

View portfolio and positions from the lagged Data API. This is not the live CLOB fill tape. Table output shows a lagged banner (`source=data_api`, `lag=true` / `lagged=true` on the analytics payload). Do not invent a lag duration.

This workflow is view-only.

## Usage

### CLI

```bash
polyterm portfolio [options]
```

### TUI

In the TUI main menu, use any of these shortcuts: `6`, `p`


## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--wallet` | string | `none` | Wallet address (or use config) |

## Examples

```bash
# Basic usage
polyterm portfolio
```

## Data Sources

- Lagged Data API (`data-api.polymarket.com`) for wallet positions — not live CLOB
- Gamma Markets REST API for market titles when a position has a market id
- Config file (`~/.polyterm/config.toml`) for default wallet address


## Related Commands

- [Position](position.md)
- [Pnl](pnl.md)
- [Simulate](simulate.md)
- [Parlay](parlay.md)
- [Exit](exit.md)

---

*Source: `polyterm/cli/commands/portfolio.py`*

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module.

When updating this feature:

- Confirm `polyterm/cli/commands/portfolio.py` still exists.
- Keep Data API positions labeled as lagged, not live CLOB.
- Do not document a lag duration.
- Run `./test_all_commands.sh` and `.venv/bin/python scripts/validate_docs.py`.
