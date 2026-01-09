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
# Full test suite (184 tests)
pytest

# Run specific test file
pytest tests/test_cli/test_cli.py -v

# Run specific test
pytest tests/test_cli/test_cli.py::TestCLI::test_cli_version -v

# Live data integration tests
pytest tests/test_live_data/ -v

# TUI tests only
pytest tests/test_tui/ -v

# Core module tests
pytest tests/test_core/ -v

# Database tests
pytest tests/test_db/ -v
```

### Running the Application
```bash
# Launch TUI (default)
polyterm

# Core CLI commands
polyterm monitor --limit 20
polyterm whales --hours 24
polyterm live-monitor --interactive
polyterm update

# Premium feature commands (v0.4.0)
polyterm arbitrage --min-spread 0.025
polyterm predict --limit 10 --horizon 24
polyterm orderbook <market_id> --chart
polyterm wallets --type smart
polyterm alerts --unread

# JSON output mode (all commands)
polyterm monitor --format json --once
polyterm arbitrage --format json
polyterm predict --format json
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
│   ├── subgraph.py       # GraphQL (deprecated by The Graph)
│   └── aggregator.py     # Multi-source aggregator with fallback
├── core/             # Business logic (significantly expanded in v0.4.0)
│   ├── scanner.py        # Market monitoring & shift detection
│   ├── analytics.py      # Basic analytics
│   ├── alerts.py         # Alert system
│   ├── whale_tracker.py  # Individual whale tracking + insider detection
│   ├── notifications.py  # Multi-channel notifications (Telegram, Discord, etc.)
│   ├── arbitrage.py      # Arbitrage scanner (intra-market, correlated, Kalshi)
│   ├── orderbook.py      # Order book analysis with ASCII charts
│   ├── predictions.py    # AI-powered multi-factor predictions
│   ├── correlation.py    # Market correlation engine
│   ├── historical.py     # Historical data API with OHLCV
│   └── portfolio.py      # Portfolio analytics (rebuilt without Subgraph)
├── db/               # Database layer (NEW in v0.4.0)
│   ├── __init__.py       # Module exports
│   ├── database.py       # SQLite database manager
│   └── models.py         # Data models (Wallet, Trade, Alert, etc.)
├── cli/              # CLI interface
│   ├── main.py           # Entry point & command registration
│   └── commands/         # Individual CLI commands
│       ├── monitor.py        # Market monitoring
│       ├── whales.py         # Whale activity
│       ├── watch.py          # Market watching
│       ├── portfolio.py      # Portfolio
│       ├── export_cmd.py     # Data export
│       ├── config_cmd.py     # Configuration
│       ├── live_monitor.py   # Live monitoring
│       ├── replay.py         # Historical replay
│       ├── arbitrage.py      # Arbitrage scanning (NEW)
│       ├── predict.py        # AI predictions (NEW)
│       ├── orderbook.py      # Order book analysis (NEW)
│       ├── wallets.py        # Wallet tracking (NEW)
│       └── alerts.py         # Alert management (NEW)
├── tui/              # Terminal UI
│   ├── controller.py     # Main loop, routes choices to screens
│   ├── menu.py           # Main menu with update checking
│   ├── logo.py           # ASCII logo (responsive to terminal width)
│   └── screens/          # Individual TUI screens
│       ├── monitor.py        # Market monitoring screen
│       ├── live_monitor.py   # Live monitor screen
│       ├── whales.py         # Whale activity screen
│       ├── watch.py          # Watch market screen
│       ├── analytics.py      # Analytics screen
│       ├── portfolio.py      # Portfolio screen
│       ├── export.py         # Export screen
│       ├── settings.py       # Settings screen
│       ├── help.py           # Help screen
│       ├── arbitrage.py      # Arbitrage screen (NEW)
│       ├── predictions.py    # Predictions screen (NEW)
│       ├── wallets.py        # Wallets screen (NEW)
│       ├── alerts_screen.py  # Alerts screen (NEW)
│       └── orderbook_screen.py # Order book screen (NEW)
└── utils/            # Utilities
    ├── config.py         # Config management (~/.polyterm/config.toml)
    ├── formatting.py     # Rich text formatting
    └── json_output.py    # JSON output utilities (NEW)
```

### Database Schema (SQLite)

Located at `~/.polyterm/data.db`:

```sql
-- Wallet profiles
wallets (address, first_seen, total_trades, total_volume, win_rate,
         avg_position_size, tags, risk_score, ...)

-- Trade history
trades (market_id, wallet_address, side, price, size, notional,
        timestamp, maker_address, taker_address, ...)

-- Alerts
alerts (alert_type, market_id, wallet_address, severity, message,
        created_at, acknowledged, ...)

-- Market snapshots
market_snapshots (market_id, probability, volume_24h, liquidity,
                  best_bid, best_ask, spread, timestamp, ...)

-- Arbitrage opportunities
arbitrage_opportunities (market1_id, market2_id, spread,
                         expected_profit, status, timestamp, ...)
```

### Key Patterns

**API Fallback**: `APIAggregator` tries Gamma API first, falls back to CLOB if needed.

**TUI Flow**: User selection → `TUIController` routes to screen → Screen gathers input → Launches CLI command via subprocess.

**Config**: TOML-based at `~/.polyterm/config.toml`, `Config` class uses dot notation (e.g., `config.get("alerts.probability_threshold")`).

**WebSocket**: Live monitor uses RTDS WebSocket at `wss://ws-live-data.polymarket.com` with polling fallback.

**Database**: SQLite via `Database` class in `polyterm/db/database.py`. All operations use context managers for connection handling.

**JSON Output**: All CLI commands support `--format json` via utilities in `polyterm/utils/json_output.py`.

### Menu Options Mapping
```
1/m = monitor        5/a = analytics      9/arb = arbitrage
2/l = live monitor   6/p = portfolio     10/pred = predictions
3/w = whales         7/e = export        11/wal = wallets
4   = watch          8/s = settings      12/alert = alerts
                                         13/ob = orderbook
u   = quick update   h/? = help
q   = quit
```

### Core Module APIs

**WhaleTracker** (`core/whale_tracker.py`):
- `process_trade(trade_data)` - Process WebSocket trade, update wallet
- `get_whale_leaderboard(limit)` - Top whales by volume
- `get_smart_money_leaderboard(limit)` - Top by win rate

**InsiderDetector** (`core/whale_tracker.py`):
- `calculate_insider_score(wallet)` - Risk score 0-100
- `analyze_wallet(wallet)` - Full insider analysis
- `get_suspicious_wallets(min_score)` - High-risk wallets

**ArbitrageScanner** (`core/arbitrage.py`):
- `scan_intra_market_arbitrage(markets)` - YES+NO < $1
- `scan_correlated_markets(markets)` - Similar events
- `KalshiArbitrageScanner.scan_cross_platform_arbitrage()` - PM vs Kalshi

**PredictionEngine** (`core/predictions.py`):
- `generate_prediction(market_id, title, horizon)` - Multi-factor prediction
- Signal types: MOMENTUM, VOLUME, WHALE, SMART_MONEY, TECHNICAL

**OrderBookAnalyzer** (`core/orderbook.py`):
- `analyze(market_id, depth)` - Full order book analysis
- `render_ascii_depth_chart(market_id)` - ASCII visualization
- `calculate_slippage(market_id, side, size)` - Slippage calc
- `detect_iceberg_orders(market_id)` - Hidden order detection

**NotificationManager** (`core/notifications.py`):
- `send(title, message, severity)` - Multi-channel send
- `test_telegram()` / `test_discord()` - Test notifications

## Testing Notes

- Tests use `responses` library for HTTP mocking
- Live data tests (`tests/test_live_data/`) hit real APIs - may fail due to data changes
- Config tests should use `tmp_path` fixture to avoid polluting user config
- When mocking `Console`, also mock `console.size.width` for responsive menu tests
- CLI compatibility tests in `tests/test_tui/test_cli_compatibility.py` verify TUI screens use valid CLI options
- Database tests create temp databases via `tmp_path` fixture

## Version Management

- Version is defined in TWO places (keep in sync):
  - `polyterm/__init__.py` - `__version__ = "x.y.z"`
  - `setup.py` - `version="x.y.z"`
- Clean build before publishing: `rm -rf dist/ build/ *.egg-info`

## Key Implementation Details

**Analytics Trending**: Uses `aggregator.get_top_markets_by_volume()` directly (not subprocess) to show static table with $1000+ volume threshold.

**Rich Colors**: Use standard colors like `bright_magenta`, `cyan`, `yellow` - avoid extended colors like `medium_purple1` for terminal compatibility.

**TUI Screens**: Most screens invoke CLI commands via subprocess. Exception: `analytics.py` trending markets displays directly using Rich tables for better UX (no live loop).

**Insider Detection Scoring**:
- Wallet age (newer = riskier): 0-25 points
- Position size relative to avg: 0-25 points
- Win rate anomaly: 0-25 points
- Trading pattern (few trades, high stakes): 0-25 points
- Risk levels: High (70+), Medium (40-69), Low (0-39)

**Arbitrage Detection**:
- Intra-market: YES + NO < $0.975 (2.5% spread minimum)
- Correlated: Title similarity + price divergence
- Cross-platform: Polymarket vs Kalshi price differences

**Prediction Signals**:
- Momentum: Price change over time window
- Volume: Volume acceleration vs baseline
- Whale: Large wallet positioning
- Smart Money: High win-rate wallet activity
- Technical: RSI-based overbought/oversold
