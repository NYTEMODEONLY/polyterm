# PolyTerm

Watch one Polymarket market from your terminal. No keys. No orders.

`polyterm watch` is the session to leave running: CLOB top-of-book, lagged Data API prints, UMA/resolution, and an honest outage line.

*a [nytemode](https://nytemode.com) project*

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/NYTEMODEONLY/polyterm/actions/workflows/ci.yml/badge.svg)](https://github.com/NYTEMODEONLY/polyterm/actions/workflows/ci.yml)

## Install and watch

Install from GitHub `main` (the source of truth; PyPI is decommissioned):

```bash
pipx install git+https://github.com/NYTEMODEONLY/polyterm.git@main
polyterm watch --market bitcoin
```

`--market` takes a Gamma slug, market ID, or search term. Ctrl+C stops the session.

No private keys. PolyTerm does not place orders. A wallet address in config is view-only.

## What `watch` shows

One live session, labeled honestly:

- **CLOB book** — best bid/ask (and size when the snapshot already has it). A connected WebSocket with no book ticks is not live: after 20s watch sets `ws_stale` and `WS connected, no book ticks`. REST fallback is labeled `clob_rest`. A missing side is an em dash, never `0`.
- **Lagged prints** — verified Data API fills (`source=data_api`, `lag=true`), plus how many this session has seen. Empty tape stays empty (`prints this session: 0`). Not live CLOB fills.
- **UMA / resolution** — Gamma/CLOB flags as they exist (`disputed`, `proposed`, `pending`, `resolved`, or `none`). Does not invent a risk letter grade.
- **Outage line** — Gamma and CLOB both down is `outage`. An unreachable Statuspage is `status_unknown`, never fake-operational.
- **Update** — `polyterm update` and the TUI reinstall from GitHub `main`.

If a wallet address is already saved, the same header shows that wallet's lagged Data API position on this market.

Details, JSON fields, and flags: [docs/cli/watch.md](docs/cli/watch.md)

## More

- TUI: `polyterm`
- Command index: [docs/README.md](docs/README.md)
- Issues: [GitHub Issues](https://github.com/NYTEMODEONLY/polyterm/issues)

## License

MIT — see [LICENSE](LICENSE).
