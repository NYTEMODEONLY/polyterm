# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PolyTerm is a terminal-based monitoring and analytics tool for PolyMarket prediction markets. It provides both a CLI and an interactive TUI (Terminal User Interface) for tracking markets, whale activity, insider patterns, arbitrage opportunities, and AI-powered predictions.

## Common Commands

### Development Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests
```bash
pytest                                                    # Full test suite
pytest tests/test_cli/test_cli.py -v                      # Specific test file
pytest tests/test_cli/test_cli.py::TestCLI::test_cli_version -v  # Specific test
pytest tests/test_live_data/ -v                           # Live API integration tests (may fail due to data changes)
```

### Running the Application
```bash
polyterm                              # Launch TUI (default)
polyterm monitor --limit 20           # CLI market monitoring
polyterm whales --hours 24            # Whale activity
polyterm arbitrage --min-spread 0.025 # Arbitrage scanning
polyterm predict --limit 10           # AI predictions
polyterm monitor --format json --once # JSON output mode (all commands support this)
```

### Building & Publishing
```bash
rm -rf dist/ build/ *.egg-info
python -m build
python -m twine upload dist/*
```

## Architecture

### Entry Points
- **CLI**: `polyterm/cli/main.py` - Click-based CLI, launches TUI if no subcommand
- **TUI**: `polyterm/tui/controller.py` - Main TUI loop with `TUIController` class

### Layer Structure

```
polyterm/
├── api/              # Data layer - API clients
│   ├── gamma.py          # Primary: Gamma REST API (/events endpoint)
│   ├── clob.py           # CLOB REST + WebSocket (wss://ws-live-data.polymarket.com)
│   └── aggregator.py     # Multi-source aggregator with fallback
├── core/             # Business logic
│   ├── scanner.py        # Market monitoring & shift detection
│   ├── whale_tracker.py  # Whale tracking + InsiderDetector class
│   ├── arbitrage.py      # Arbitrage scanner (intra-market, correlated, Kalshi)
│   ├── orderbook.py      # Order book analysis with ASCII charts
│   ├── predictions.py    # AI-powered multi-factor predictions
│   └── notifications.py  # Multi-channel notifications
├── db/               # Database layer (SQLite at ~/.polyterm/data.db)
│   ├── database.py       # SQLite database manager
│   └── models.py         # Data models (Wallet, Trade, Alert, etc.)
├── cli/              # CLI interface
│   ├── main.py           # Entry point & command registration
│   └── commands/         # Individual CLI commands
├── tui/              # Terminal UI
│   ├── controller.py     # Main loop, routes choices to screens
│   ├── menu.py           # Main menu with update checking
│   └── screens/          # Individual TUI screens
└── utils/            # Utilities
    ├── config.py         # Config management (~/.polyterm/config.toml)
    └── json_output.py    # JSON output utilities
```

### Key Patterns

**API Fallback**: `APIAggregator` tries Gamma API first, falls back to CLOB if needed.

**TUI Flow**: User selection → `TUIController` routes to screen → Screen gathers input → Launches CLI command via subprocess.

**Config**: TOML-based at `~/.polyterm/config.toml`, `Config` class uses dot notation (e.g., `config.get("alerts.probability_threshold")`).

**WebSocket**: Live monitor uses RTDS WebSocket at `wss://ws-live-data.polymarket.com` with polling fallback.

**Database**: SQLite via `Database` class. All operations use context managers for connection handling.

**JSON Output**: All CLI commands support `--format json` via utilities in `polyterm/utils/json_output.py`.

### TUI Menu Options
```
1/m = monitor        5/a = analytics      9/arb = arbitrage
2/l = live monitor   6/p = portfolio     10/pred = predictions
3/w = whales         7/e = export        11/wal = wallets
4   = watch          8/s = settings      12/alert = alerts
                                         13/ob = orderbook
u   = quick update   h/? = help
q   = quit
```

## Testing Notes

- Tests use `responses` library for HTTP mocking
- Live data tests (`tests/test_live_data/`) hit real APIs - may fail due to data changes
- Config tests should use `tmp_path` fixture to avoid polluting user config
- When mocking `Console`, also mock `console.size.width` for responsive menu tests
- CLI compatibility tests in `tests/test_tui/test_cli_compatibility.py` verify TUI screens use valid CLI options
- Database tests create temp databases via `tmp_path` fixture

## Version Management

Version is defined in TWO places (keep in sync):
- `polyterm/__init__.py` - `__version__ = "x.y.z"`
- `setup.py` - `version="x.y.z"`

## Key Implementation Details

**Rich Colors**: Use standard colors like `bright_magenta`, `cyan`, `yellow` - avoid extended colors like `medium_purple1` for terminal compatibility.

**TUI Screens**: Most screens invoke CLI commands via subprocess. Exception: `analytics.py` trending markets displays directly using Rich tables (uses `aggregator.get_top_markets_by_volume()` directly).

**Insider Detection Scoring** (`core/whale_tracker.py`):
- Wallet age (newer = riskier): 0-25 points
- Position size relative to avg: 0-25 points
- Win rate anomaly: 0-25 points
- Trading pattern (few trades, high stakes): 0-25 points
- Risk levels: High (70+), Medium (40-69), Low (0-39)

**Arbitrage Detection** (`core/arbitrage.py`):
- Intra-market: YES + NO < $0.975 (2.5% spread minimum)
- Correlated: Title similarity + price divergence
- Cross-platform: Polymarket vs Kalshi price differences

**Prediction Signals** (`core/predictions.py`):
- Momentum: Price change over time window
- Volume: Volume acceleration vs baseline
- Whale: Large wallet positioning
- Smart Money: High win-rate wallet activity
- Technical: RSI-based overbought/oversold
