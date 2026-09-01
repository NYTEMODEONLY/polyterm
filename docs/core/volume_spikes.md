# Volume Spikes

> Gamma 24h volume heuristic. This is not whale identity or a trade feed.

## Overview

The volume-spikes module lists active markets whose Gamma `volume24hr` is at least a threshold. It is the honest implementation behind the default `polyterm whales` path. It does not invent trader addresses, timestamps of individual fills, or transaction hashes.

Wallet-level whale prints live in `polyterm whales --wallets` (`scan_whale_prints` / `PrintScanner`). Those fills are lagged Data API rows, not live CLOB. Agent `wallet.whales` still uses `WalletIntelligence.live_whales`.

## Usage

```python
from polyterm.core.volume_spikes import detect_high_volume_markets, EVIDENCE_LEVEL

markets = detect_high_volume_markets(gamma_client, min_volume=10000)
for market in markets:
    assert market.evidence_level == EVIDENCE_LEVEL
    assert "trader" not in market.to_dict()
```

## Key Types

### `HighVolumeMarket`

| Field | Type | Description |
|-------|------|-------------|
| `market_id` | `str` | Gamma market ID |
| `market_title` | `str` | Market title or question |
| `volume_24hr` | `float` | Gamma 24h volume |
| `last_price` | `float` | Last trade price or YES price fallback |
| `outcome_lean` | `str` | `YES` / `NO` / `MIXED` / `Unknown` from YES-price thresholds |
| `timestamp` | `int` | Observation time (not a trade time) |
| `evidence_level` | `str` | Always `gamma_volume24hr_heuristic` |

There is no `trader` field.

### `detect_high_volume_markets(gamma_client, min_volume=10000, limit=50, now=None)`

Fetch active Gamma markets and keep those with `volume24hr >= min_volume`. Results are sorted by volume descending.

## Evidence Level

`EVIDENCE_LEVEL = "gamma_volume24hr_heuristic"`

`DISCLOSURE` states that this is market-level 24h volume, not a whale trade, wallet, or transaction.

Outcome lean uses YES price thresholds:

- `> 0.65` → YES
- `< 0.35` → NO
- otherwise → MIXED

That lean is a price snapshot, not a whale side.

## Data Sources

- Gamma Markets REST API (`volume24hr`, `outcomePrices`, `lastTradePrice`)
- Not Data API `/trades`
- Not CLOB WebSocket maker addresses

## Related

- CLI: [whales](../cli/whales.md)
- TUI: [whales](../tui/screens/whales.md)
- Wallet-level whales: [wallet_intelligence](wallet_intelligence.md)
- Legacy wrapper: [analytics](analytics.md) `track_whale_trades`

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module.

When updating this feature:

- Confirm `polyterm/core/volume_spikes.py` still exists.
- Do not document a `trader` field or whale identity on this path.
- Keep `--wallets` as the wallet-level alternative.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Pages that depend on live market data should name Gamma.
- New modules should have a dedicated page rather than relying only on the index.
