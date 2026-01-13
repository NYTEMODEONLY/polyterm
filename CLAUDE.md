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
polyterm tutorial                     # Interactive tutorial for new users
polyterm glossary                     # Prediction market terminology
polyterm simulate -i                  # P&L calculator (interactive)
polyterm monitor --limit 20           # CLI market monitoring
polyterm whales --hours 24            # Whale activity
polyterm arbitrage --min-spread 0.025 # Arbitrage scanning
polyterm predict --limit 10           # AI predictions
polyterm risk --market "bitcoin"      # Market risk assessment
polyterm follow --list                # Copy trading / followed wallets
polyterm parlay -i                    # Parlay calculator (interactive)
polyterm bookmarks --list             # View saved markets
polyterm dashboard                    # Quick overview of activity
polyterm chart -m "bitcoin"           # ASCII price history chart
polyterm compare -i                   # Compare markets side by side
polyterm size -i                      # Position size calculator (Kelly Criterion)
polyterm recent                       # View recently accessed markets
polyterm pricealert -i                # Set price target alerts
polyterm calendar --days 7            # View upcoming resolutions
polyterm fees -i                      # Calculate fees and slippage
polyterm stats -m "bitcoin"           # Market statistics and technicals
polyterm search --min-volume 100000   # Advanced market search
polyterm monitor --show-quality       # Show volume quality indicators
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
│   ├── risk_score.py     # Market risk scoring system (A-F grades)
│   ├── uma_tracker.py    # UMA oracle dispute risk analysis
│   ├── wash_trade_detector.py  # Wash trade detection indicators
│   ├── charts.py         # ASCII chart generation (line, bar, sparkline)
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
    ├── json_output.py    # JSON output utilities
    ├── errors.py         # Centralized error handling with user-friendly messages
    ├── tips.py           # Contextual tips and hints system
    └── contextual_help.py # Screen-specific help content
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
                                         14/risk = risk assessment
                                         15/follow = copy trading
                                         16/parlay = parlay calculator
                                         17/bm = bookmarks

d   = dashboard      t   = tutorial       g   = glossary
sim = simulate       ch  = chart          cmp = compare
sz  = size           rec = recent         pa  = pricealert
cal = calendar       fee = fees           st  = stats
sr  = search         pos = position       nt  = notes
pr  = presets        sent = sentiment     corr = correlate
ex  = exitplan       dp  = depth          tr  = trade
tl  = timeline       an  = analyze        jn  = journal
hot = hot markets    pnl = profit/loss    u   = quick update
h/? = help           q   = quit
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

**Market Risk Scoring** (`core/risk_score.py`):
- 6 risk factors with weighted scores: resolution clarity (25%), liquidity (20%), time risk (15%), volume quality (15%), spread (15%), category risk (10%)
- Grades: A (0-20), B (21-35), C (36-50), D (51-70), F (71+)
- Includes warnings and recommendations

**Copy Trading / Wallet Following** (`cli/commands/follow.py`, `db/database.py`):
- Follow up to 10 wallets
- Track win rate, volume, trade count, avg position size
- Interactive mode and CLI options (--add, --remove, --list)

**Parlay Calculator** (`cli/commands/parlay.py`):
- Combine multiple bets for higher potential payouts
- Calculates combined probability, decimal/American odds
- Shows expected value and risk level
- Fee-adjusted payouts (2% on winnings)

**Error Handling** (`utils/errors.py`):
- Centralized user-friendly error messages
- API error handling with suggestions (timeouts, rate limits, etc.)
- Predefined error messages for common scenarios

**UMA Dispute Tracking** (`core/uma_tracker.py`):
- Analyzes markets for resolution dispute risk
- Factors: subjectivity, category, resolution source clarity, time risk
- Risk levels: Low, Medium, High, Very High
- Used in risk assessment command

**Wash Trade Detection** (`core/wash_trade_detector.py`):
- Identifies potential artificial volume
- Indicators: volume/liquidity ratio, trader concentration, size uniformity, side balance
- Based on research showing ~25% of Polymarket volume may be wash trading
- Risk levels: Low, Medium, High, Very High
- Integrated into monitor command with `--show-quality` flag

**Market Bookmarks** (`cli/commands/bookmarks.py`, `db/database.py`):
- Save favorite markets for quick access
- Add notes to bookmarks
- Interactive and CLI modes (--list, --add, --remove)
- Stored in local SQLite database

**Dashboard** (`cli/commands/dashboard.py`):
- Quick overview of market activity
- Shows top volume markets, bookmarks, alerts, followed wallets
- Perfect for daily check-ins
- Available via `d` shortcut or `polyterm dashboard`

**ASCII Charts** (`core/charts.py`):
- Terminal-based price visualization
- Line charts with Bresenham's line algorithm
- Sparklines for compact display (8 levels: ▁▂▃▄▅▆▇█)
- Bar charts and comparison charts
- Used by chart command for price history

**Price Charts** (`cli/commands/chart.py`):
- View price history for any market
- Supports full charts and compact sparklines
- Customizable timeframe (hours) and dimensions
- Data from database snapshots

**Market Comparison** (`cli/commands/compare.py`):
- Compare up to 4 markets side by side
- Shows sparklines, price changes, volumes
- Interactive market selection
- Identifies potential arbitrage (combined probability analysis)

**Position Size Calculator** (`cli/commands/size.py`):
- Kelly Criterion-based bet sizing
- Calculates edge, expected value per dollar
- Full Kelly vs fractional Kelly (quarter, half)
- Fixed percentage alternatives (1%, 2%, 5%)
- Outcome projections (profit if win, loss if lose)

**Recently Viewed Markets** (`cli/commands/recent.py`, `db/database.py`):
- Automatic tracking of viewed markets
- View count for frequently accessed markets
- Quick return to markets being researched
- Clear history option
- Stored in SQLite `recently_viewed` table

**Price Alerts** (`cli/commands/pricealert.py`, `db/database.py`):
- Set alerts when markets hit target prices
- Direction-aware (above/below target)
- Interactive management (add, list, check, remove)
- Stored in SQLite `price_alerts` table
- Check command to verify triggered alerts

**Market Calendar** (`cli/commands/calendar.py`):
- View upcoming market resolutions
- Filter by days ahead, category, bookmarked
- Grouped by date with countdown
- Helps plan exits before resolution

**Fee & Slippage Calculator** (`cli/commands/fees.py`):
- Polymarket fee structure (0% maker, 2% taker on winnings)
- Slippage estimation from order book
- Net profit/loss projections
- Gas fee estimates (Polygon network)

**Market Statistics** (`cli/commands/stats.py`):
- Volatility calculation (standard deviation of returns)
- Trend analysis (linear regression slope)
- RSI (Relative Strength Index) - 14 period
- Momentum detection (accelerating/decelerating)
- Price range analysis (high/low/range)
- Certainty measurement (distance from 50%)

**Advanced Search** (`cli/commands/search.py`):
- Filter by category, volume, liquidity, price range
- Filter by resolution date (ending soon)
- Multiple sort options (volume, liquidity, price, recent)
- Interactive and CLI modes
