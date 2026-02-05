# PolyTerm

A powerful, terminal-based monitoring and analytics tool for PolyMarket prediction markets. Track market shifts, whale activity, insider patterns, arbitrage opportunities, and signal-based predictions—all from your command line.

*a [nytemode](https://nytemode.com) project*

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/polyterm.svg)](https://pypi.org/project/polyterm/)

![PolyTerm Screenshot](screenshot.png)

---

## Quick Start

### Option 1: Install from PyPI (Recommended)
```bash
pipx install polyterm
```

### Option 2: One-Command Install
```bash
curl -sSL https://raw.githubusercontent.com/NYTEMODEONLY/polyterm/main/install.sh | bash
```

### Option 3: Manual Install
```bash
git clone https://github.com/NYTEMODEONLY/polyterm.git
cd polyterm
pip install -e .
```

**Launch PolyTerm:**
```bash
polyterm
```

---

## Features Overview

### Core Features
| Feature | Command | Description |
|---------|---------|-------------|
| Market Monitoring | `polyterm monitor` | Real-time market tracking with live updates |
| Live Monitor | `polyterm live-monitor` | Dedicated terminal window for focused monitoring |
| Whale Activity | `polyterm whales` | Volume-based whale detection |
| Watch Markets | `polyterm watch` | Track specific markets with alerts |
| Export Data | `polyterm export` | Export to JSON/CSV |
| Historical Replay | `polyterm replay` | Replay market history |

### Trading & Crypto
| Feature | Command | Description |
|---------|---------|-------------|
| 15-Minute Crypto | `polyterm crypto15m` | Monitor BTC, ETH, SOL, XRP 15-minute markets |
| My Wallet | `polyterm mywallet` | VIEW-ONLY wallet tracking (positions, P&L) |
| Quick Trade | `polyterm quicktrade` | Trade analysis with direct Polymarket links |

### Premium Features
| Feature | Command | Description |
|---------|---------|-------------|
| Arbitrage Scanner | `polyterm arbitrage` | Find cross-market profit opportunities |
| Signal-based Predictions | `polyterm predict` | Multi-factor market predictions using live data |
| Order Book Analysis | `polyterm orderbook` | Depth charts, slippage, icebergs |
| Wallet Tracking | `polyterm wallets` | Smart money & whale wallet analysis |
| Alert Management | `polyterm alerts` | Multi-channel notification system |
| Risk Assessment | `polyterm risk` | Market risk scoring (A-F grades) |
| Copy Trading | `polyterm follow` | Follow successful wallets |

### Tools & Calculators
| Feature | Command | Description |
|---------|---------|-------------|
| Dashboard | `polyterm dashboard` | Quick overview of activity |
| Simulate P&L | `polyterm simulate -i` | Interactive P&L calculator |
| Parlay Calculator | `polyterm parlay -i` | Combine multiple bets |
| Position Size | `polyterm size -i` | Kelly Criterion bet sizing |
| Fee Calculator | `polyterm fees -i` | Calculate fees and slippage |
| Price Alerts | `polyterm pricealert -i` | Set target price notifications |

### Research & Analysis
| Feature | Command | Description |
|---------|---------|-------------|
| Market Search | `polyterm search` | Advanced filtering and search |
| Market Stats | `polyterm stats -m "market"` | Volatility, RSI, trends |
| Price Charts | `polyterm chart -m "market"` | ASCII price history |
| Compare Markets | `polyterm compare -i` | Side-by-side comparison |
| Calendar | `polyterm calendar` | Upcoming resolutions |
| Bookmarks | `polyterm bookmarks` | Save favorite markets |
| Recent Markets | `polyterm recent` | Recently viewed markets |

### Learning
| Feature | Command | Description |
|---------|---------|-------------|
| Tutorial | `polyterm tutorial` | Interactive beginner guide |
| Glossary | `polyterm glossary` | Prediction market terminology |

---

## CLI Commands

### Market Monitoring
```bash
# Monitor top markets
polyterm monitor --limit 20

# Monitor with JSON output (for scripting)
polyterm monitor --format json --limit 10 --once

# Sort by different criteria
polyterm monitor --sort volume
polyterm monitor --sort probability
polyterm monitor --sort recent
```

### Whale Activity
```bash
# Find high-volume markets
polyterm whales --hours 24 --min-amount 50000

# JSON output
polyterm whales --format json
```

### Arbitrage Scanner
```bash
# Scan for arbitrage opportunities
polyterm arbitrage --min-spread 0.025 --limit 10

# Include Kalshi cross-platform arbitrage
polyterm arbitrage --include-kalshi

# JSON output for automation
polyterm arbitrage --format json
```

**What it detects:**
- **Intra-market**: YES + NO prices < $1.00 (guaranteed profit)
- **Correlated markets**: Similar events with price discrepancies
- **Cross-platform**: Polymarket vs Kalshi price differences

### Signal-based Predictions
```bash
# Generate predictions for top markets
polyterm predict --limit 10 --horizon 24

# Predict specific market
polyterm predict --market <market_id>

# High-confidence predictions only
polyterm predict --min-confidence 0.7

# JSON output
polyterm predict --format json
```

**Prediction signals include:**
- Price momentum (trend analysis)
- Volume acceleration
- Whale behavior patterns
- Smart money positioning
- Technical indicators (RSI)
- Time to resolution

### Order Book Analysis
```bash
# Analyze order book
polyterm orderbook <market_token_id>

# Show ASCII depth chart
polyterm orderbook <market_token_id> --chart

# Calculate slippage for large order
polyterm orderbook <market_token_id> --slippage 10000 --side buy

# Full analysis with depth
polyterm orderbook <market_token_id> --depth 50 --chart
```

**What you get:**
- Best bid/ask and spread
- Bid/ask depth visualization
- Support/resistance levels
- Large order detection (icebergs)
- Slippage calculations
- Liquidity imbalance warnings

### Wallet Tracking
```bash
# View whale wallets (by volume)
polyterm wallets --type whales

# View smart money (>70% win rate)
polyterm wallets --type smart

# View suspicious wallets (high risk score)
polyterm wallets --type suspicious

# Analyze specific wallet
polyterm wallets --analyze <wallet_address>

# Track a wallet for alerts
polyterm wallets --track <wallet_address>

# JSON output
polyterm wallets --format json
```

### Alert Management
```bash
# View recent alerts
polyterm alerts --limit 20

# View only unread alerts
polyterm alerts --unread

# Filter by type
polyterm alerts --type whale
polyterm alerts --type insider
polyterm alerts --type arbitrage
polyterm alerts --type smart_money

# Acknowledge an alert
polyterm alerts --ack <alert_id>

# Test notification channels
polyterm alerts --test-telegram
polyterm alerts --test-discord
```

### 15-Minute Crypto Markets
```bash
# Monitor all 15M crypto markets
polyterm crypto15m

# Monitor specific crypto
polyterm crypto15m -c BTC          # Bitcoin only
polyterm crypto15m -c ETH          # Ethereum only

# Interactive mode with trade analysis
polyterm crypto15m -i

# Get direct Polymarket links
polyterm crypto15m --links

# JSON output
polyterm crypto15m --format json --once
```

**Direct Polymarket Crypto Links:**
- 15-Minute: https://polymarket.com/crypto/15M
- Hourly: https://polymarket.com/crypto/hourly
- Daily: https://polymarket.com/crypto/daily
- By Coin: /crypto/bitcoin, /crypto/ethereum, /crypto/solana, /crypto/xrp

**Supported Cryptocurrencies:** BTC, ETH, SOL, XRP

### My Wallet (VIEW-ONLY)
```bash
# Connect your wallet (VIEW-ONLY - no private keys)
polyterm mywallet --connect

# View open positions
polyterm mywallet -p

# View trade history
polyterm mywallet -h

# View P&L summary
polyterm mywallet --pnl

# Interactive mode
polyterm mywallet -i

# View any wallet
polyterm mywallet -a 0x123...

# Disconnect wallet
polyterm mywallet --disconnect
```

**Important:** This is a VIEW-ONLY feature. No private keys are stored or required. You simply provide your wallet address to track your Polymarket activity.

### Quick Trade Preparation
```bash
# Prepare a trade with analysis
polyterm quicktrade -m "bitcoin" -a 200 -s yes

# Prepare and open browser
polyterm quicktrade -m "trump" -a 50 -s no -o

# Interactive mode
polyterm quicktrade -i

# JSON output
polyterm quicktrade -m "bitcoin" --format json
```

**What you get:**
- Entry price and share calculation
- Profit/loss scenarios (win vs lose)
- Fee calculation (2% taker fee)
- ROI and breakeven analysis
- Expected value calculation
- Direct link to trade on Polymarket

### Watch Specific Markets
```bash
# Watch with price threshold alerts
polyterm watch <market_id> --threshold 5

# Watch with custom interval
polyterm watch <market_id> --threshold 3 --interval 30
```

### Export Data
```bash
# Export to JSON
polyterm export --market <market_id> --format json --output data.json

# Export to CSV
polyterm export --market <market_id> --format csv --output data.csv
```

### Configuration
```bash
# List all settings
polyterm config --list

# Get specific setting
polyterm config --get alerts.probability_threshold

# Set a value
polyterm config --set alerts.probability_threshold 10.0
```

---

## Interactive TUI

Launch the interactive terminal interface:
```bash
polyterm
```

**First-time users** will be guided through an interactive tutorial covering prediction market basics, whale tracking, and arbitrage detection.

### Main Menu
```
Page 1:                                  Page 2:
1/mon  = monitor     9/arb  = arbitrage  d   = dashboard      t   = tutorial
2/l    = live mon   10/pred = predictions sim = simulate       g   = glossary
3/w    = whales     11/wal  = wallets    ch  = chart           cmp = compare
4      = watch      12/alert= alerts     sz  = size            rec = recent
5/a    = analytics  13/ob   = orderbook  pa  = pricealert      cal = calendar
6/p    = portfolio  14/risk = risk       fee = fees            st  = stats
7/e    = export     15/follow = copy     sr  = search          nt  = notes
8/s    = settings   16/parlay = parlay   pr  = presets         sent= sentiment
                    17/bm   = bookmarks  corr= correlate       dp  = depth

c15 = 15m crypto     mw  = my wallet     qt  = quick trade
hot = hot markets    pnl = profit/loss    u   = quick update

h/? = help           m/+ = next page      q   = quit
```

### Navigation
- **Numbers**: Press `1-17` for numbered features
- **Shortcuts**: Use the abbreviation shortcuts shown above
- **Pagination**: Press `m` or `+` to see more options, `b` or `-` to go back
- **Trading**: `c15` for 15M crypto, `mw` for wallet, `qt` for quick trade
- **Help**: Press `h` or `?` for documentation
- **Tutorial**: Press `t` to launch the interactive tutorial
- **Glossary**: Press `g` for prediction market terminology
- **Quit**: Press `q` to exit

---

## Notification Setup

### Telegram Notifications
1. Create a bot via [@BotFather](https://t.me/botfather)
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Configure in PolyTerm:
```bash
polyterm config --set notification.telegram.enabled true
polyterm config --set notification.telegram.bot_token "YOUR_BOT_TOKEN"
polyterm config --set notification.telegram.chat_id "YOUR_CHAT_ID"
```

### Discord Notifications
1. Create a webhook in your Discord server (Server Settings → Integrations → Webhooks)
2. Configure in PolyTerm:
```bash
polyterm config --set notification.discord.enabled true
polyterm config --set notification.discord.webhook_url "YOUR_WEBHOOK_URL"
```

### Test Notifications
```bash
polyterm alerts --test-telegram
polyterm alerts --test-discord
```

---

## JSON Output Mode

All commands support `--format json` for scripting and automation:

```bash
# Get markets as JSON
polyterm monitor --format json --limit 5 --once | jq '.markets[] | select(.probability > 0.8)'

# Get arbitrage opportunities
polyterm arbitrage --format json | jq '.opportunities[] | select(.net_profit > 2)'

# Get predictions
polyterm predict --format json | jq '.predictions[] | select(.confidence > 0.7)'

# Get wallet data
polyterm wallets --format json --type smart | jq '.wallets[] | select(.win_rate > 0.8)'
```

---

## Database & Storage

PolyTerm stores data locally in SQLite:
- **Location**: `~/.polyterm/data.db`
- **Tables**: wallets, trades, alerts, market_snapshots, arbitrage_opportunities

### Data Tracked
- Wallet profiles with win rates and tags
- Trade history with maker/taker addresses
- Alert history with severity scoring
- Market snapshots for historical analysis
- Arbitrage opportunities log

---

## Configuration

Configuration stored in `~/.polyterm/config.toml`:

```toml
[api]
gamma_base_url = "https://gamma-api.polymarket.com"
clob_rest_endpoint = "https://clob.polymarket.com"
clob_endpoint = "wss://ws-live-data.polymarket.com"

[whale_tracking]
min_whale_trade = 10000
min_smart_money_win_rate = 0.70
min_smart_money_trades = 10

[arbitrage]
min_spread = 0.025
fee_rate = 0.02

[notification]
[notification.telegram]
enabled = false
bot_token = ""
chat_id = ""

[notification.discord]
enabled = false
webhook_url = ""

[notification.system]
enabled = true

[notification.sound]
enabled = true
critical_only = true

[alerts]
probability_threshold = 5.0
check_interval = 60

[display]
refresh_rate = 2
max_markets = 20
```

---

## Architecture

```
polyterm/
├── api/              # API clients
│   ├── gamma.py          # Gamma REST API
│   ├── clob.py           # CLOB REST + WebSocket
│   └── aggregator.py     # Multi-source aggregator
├── core/             # Business logic
│   ├── whale_tracker.py  # Whale & insider detection
│   ├── notifications.py  # Multi-channel alerts
│   ├── arbitrage.py      # Arbitrage scanner
│   ├── orderbook.py      # Order book analysis
│   ├── predictions.py    # Signal-based predictions
│   ├── correlation.py    # Market correlations
│   ├── historical.py     # Historical data API
│   └── portfolio.py      # Portfolio analytics
├── db/               # Database layer
│   ├── database.py       # SQLite manager
│   └── models.py         # Data models
├── cli/              # CLI commands
│   ├── main.py           # Entry point
│   └── commands/         # Individual commands
├── tui/              # Terminal UI
│   ├── controller.py     # Main loop
│   ├── menu.py           # Main menu
│   └── screens/          # TUI screens
└── utils/            # Utilities
    ├── config.py         # Configuration
    ├── json_output.py    # JSON formatting
    └── formatting.py     # Rich formatting
```

---

## Testing

```bash
# Full test suite
pytest

# Specific test categories
pytest tests/test_core/ -v          # Core logic tests
pytest tests/test_db/ -v            # Database tests
pytest tests/test_cli/ -v           # CLI tests
pytest tests/test_tui/ -v           # TUI tests
pytest tests/test_api/ -v           # API tests
pytest tests/test_live_data/ -v     # Live API tests (may fail due to data changes)
```

---

## Development

### Setup
```bash
git clone https://github.com/NYTEMODEONLY/polyterm.git
cd polyterm
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Build & Publish
```bash
rm -rf dist/ build/ *.egg-info
python -m build
python -m twine upload dist/*
```

---

## What's New in v0.7.6

### Bug Fixes
- **Notification config schema mismatch** - The `notify` command used flat config keys (`notifications.desktop`) that didn't match the default config structure. Added missing defaults so settings persist correctly across sessions
- **Position command crash** - Missing try-except around JSON parsing of outcome prices in interactive position tracking
- **Predictions RSI cleanup** - Removed misleading `0.001` fallback for avg_loss in RSI calculation; now correctly uses 0 with the existing guard clause

### Test Suite
- **183/183 tests passing** (2 skipped for deprecated endpoints)

---

## What's New in v0.7.5

### Critical Fixes
- **Arbitrage fee calculations corrected** - Intra-market arb was overcharging fees (2% on full $1 payout instead of 2% on winnings only). Correlated market arb was double-charging fees on both sides instead of just the winning position
- **Correlation engine now functional** - `find_correlated_markets()` was completely broken due to an empty market_ids placeholder; now queries database for all tracked markets
- **Prediction signals: buy/sell classification fixed** - Whale and smart money signals were misclassifying trades using OR logic (`side == 'BUY' or outcome == 'YES'`), counting every YES-outcome trade as a buy regardless of actual direction

### Bug Fixes
- **Charts Y-axis labels fixed** - Probabilities >= 100% were displayed as raw values (e.g., "1%" instead of "100%")
- **Orderbook slippage division-by-zero** - Added guard when best_price is 0
- **TUI screen crash protection** - Screen errors now return to menu instead of crashing the entire TUI
- **Live monitor cleanup** - Replaced `os._exit(0)` with proper `sys.exit(0)` to prevent resource leaks and zombie processes
- **Menu pagination** - Fixed unnecessary redraws when pressing next on last page or back on first page

### Test Suite
- **183/183 tests passing** (2 skipped for deprecated endpoints)

---

## What's New in v0.7.4

### Critical Fixes
- **MyWallet: Removed broken SubgraphClient dependency** - The PolyMarket Subgraph was deprecated by The Graph, leaving `mywallet` completely non-functional. Now uses local database for position/trade tracking instead
- **Chart: Fixed misleading synthetic data** - When no price history exists, charts now show an honest flat line at current price instead of fabricating a fake dip-recovery pattern
- **Market freshness: Fixed perpetual market detection** - Open-ended markets without end dates (e.g., "Will X happen?") were incorrectly flagged as stale; now checks the `active` flag as fallback

### Test Suite
- **183/183 tests passing** (2 skipped for deprecated endpoints)

---

## What's New in v0.7.3

### Performance
- **Added compound database indexes** - New indexes on trades(market_id,timestamp), market_snapshots(market_id,timestamp), positions(entry_date), and alerts(acknowledged) for faster queries

### Reliability
- **Config validation** - All threshold settings now have type checking and range validation (e.g., probability_threshold must be 0.1-100.0, min_smart_money_win_rate must be 0.0-1.0)
- **Subgraph deprecation warning** - SubgraphClient now logs a clear deprecation warning directing users to GammaClient/CLOBClient

### Test Suite
- **183/183 tests passing** (2 skipped for deprecated endpoints)

---

## What's New in v0.7.2

### Bug Fixes
- **Fixed division-by-zero in whales command** - Empty whale trade results no longer crash when calculating average volume per market

### Code Quality
- **Eliminated all 44 bare `except:` handlers** - Replaced with `except Exception:` across 24 files (CLI commands, core modules, TUI screens, API layer, utilities) for better debugging and proper exception handling

### Test Suite
- **183/183 tests passing** (2 skipped for deprecated endpoints)

---

## What's New in v0.7.1

### Architecture Improvements
- **TUI dispatch table refactor** - Replaced 77-line elif chain with O(1) dictionary dispatch for all 80+ screen routes
- **Database auto-cleanup** - Automatic pruning of old records (>30 days) when database exceeds 10,000 rows, preventing unbounded growth
- **WebSocket auto-reconnection** - Live monitor reconnects automatically with exponential backoff (up to 5 attempts) and re-subscribes to trade feeds

### Bug Fixes
- **Fixed order book depth calculation** - Now correctly shows share depth (not notional value) in `bid_depth`/`ask_depth` fields, with separate notional tracking
- **Fixed UMA tracker timezone crash** - Resolved `TypeError` when comparing timezone-aware and naive datetimes in resolution risk analysis

### Test Suite
- **183/183 tests passing** (2 skipped for deprecated endpoints)
- Updated TUI integration tests to work with new dispatch table pattern

---

## What's New in v0.7.0

### Bug Fixes
- **Fixed arbitrage profit calculations** - Corrected percentage math and fee calculations for intra-market and correlated market arbitrage detection
- **Fixed smart money signal accuracy** - Corrected average win rate calculation that was using wrong denominator
- **Fixed all bare exception handlers** - Replaced `except:` with `except Exception:` across API and core layers for better debugging

### Reliability Improvements
- **API retry logic with exponential backoff** - Gamma and CLOB API clients now retry on 429 rate limits, 5xx server errors, timeouts, and connection failures (up to 3 attempts with backoff)
- **SQLite foreign key enforcement** - Enabled `PRAGMA foreign_keys = ON` to prevent orphaned records and ensure data integrity
- **Request timeouts** - All API requests now have 15-second timeouts to prevent indefinite hangs

### Test Suite
- **183/183 tests passing** (2 skipped for deprecated endpoints)
- Fixed live data tests to handle markets with end dates spanning calendar years
- Fixed TUI shortcut tests to match current menu pagination system
- Added proper wallet record creation in test fixtures to satisfy foreign key constraints

---

## Known Limitations

- **Portfolio tracking**: Limited due to Subgraph API deprecation (uses local trade history)
- **Individual trades**: WebSocket required for real-time individual trade data
- **Kalshi integration**: Requires Kalshi API key for cross-platform features

---

## Support

- **Issues**: [GitHub Issues](https://github.com/NYTEMODEONLY/polyterm/issues)
- **Documentation**: See this README and inline `--help`
- **Updates**: `polyterm update` or `pipx upgrade polyterm`

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

**Built for the PolyMarket community**

*Your terminal window to prediction market alpha*

*a [nytemode](https://nytemode.com) project*
