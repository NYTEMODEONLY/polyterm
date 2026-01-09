# PolyTerm 📊

A powerful, terminal-based monitoring and analytics tool for PolyMarket prediction markets. Track market shifts, whale activity, insider patterns, arbitrage opportunities, and AI-powered predictions—all from your command line.

*a [nytemode](https://nytemode.com) project*

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/polyterm.svg)](https://pypi.org/project/polyterm/)
[![Live Data](https://img.shields.io/badge/Data-Live%202025-brightgreen.svg)](API_SETUP.md)

---

## What's New in v0.4.0

**Major Feature Release** - PolyTerm is now a comprehensive trading analytics platform:

- **SQLite Database** - Persistent local storage for wallets, trades, alerts, and market data
- **Individual Whale Tracking** - Track specific wallets via WebSocket maker_address
- **Insider Detection Engine** - Risk scoring system (0-100) to identify suspicious patterns
- **Smart Money Identification** - Find wallets with >70% win rates
- **Arbitrage Scanner** - Cross-market and cross-platform (Kalshi) arbitrage detection
- **Order Book Analysis** - ASCII depth charts, iceberg detection, slippage calculator
- **AI-Powered Predictions** - Multi-factor signals with confidence scoring
- **Market Correlation Engine** - Find related markets and correlation breaks
- **Multi-Channel Alerts** - Telegram, Discord, system notifications, email, sound
- **JSON Output Mode** - All commands support `--format json` for scripting
- **5 New CLI Commands** - arbitrage, predict, orderbook, wallets, alerts
- **5 New TUI Screens** - Premium features accessible from interactive menu

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

### Core Features (Free)
| Feature | Command | Description |
|---------|---------|-------------|
| Market Monitoring | `polyterm monitor` | Real-time market tracking with live updates |
| Live Monitor | `polyterm live-monitor` | Dedicated terminal window for focused monitoring |
| Whale Activity | `polyterm whales` | Volume-based whale detection |
| Watch Markets | `polyterm watch` | Track specific markets with alerts |
| Export Data | `polyterm export` | Export to JSON/CSV |
| Historical Replay | `polyterm replay` | Replay market history |

### Premium Features (v0.4.0)
| Feature | Command | Description |
|---------|---------|-------------|
| Arbitrage Scanner | `polyterm arbitrage` | Find cross-market profit opportunities |
| AI Predictions | `polyterm predict` | Multi-factor market predictions |
| Order Book Analysis | `polyterm orderbook` | Depth charts, slippage, icebergs |
| Wallet Tracking | `polyterm wallets` | Smart money & whale wallet analysis |
| Alert Management | `polyterm alerts` | Multi-channel notification system |

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

### AI Predictions
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

### Main Menu
```
   1 📊 Monitor Markets - Real-time market tracking
   2 🔴 Live Monitor - Dedicated terminal window
   3 🐋 Whale Activity - High-volume markets
   4 👁  Watch Market - Track specific market
   5 📈 Market Analytics - Trends and predictions
   6 💼 Portfolio - View your positions
   7 📤 Export Data - Export to JSON/CSV
   8 ⚙️  Settings - Configuration

   9 💰 Arbitrage - Scan for arbitrage opportunities
  10 🤖 Predictions - AI-powered market predictions
  11 👛 Wallets - Smart money tracking
  12 🔔 Alerts - Manage notifications
  13 📖 Order Book - Analyze market depth

   h ❓ Help - View documentation
   q 🚪 Quit - Exit PolyTerm
```

### Navigation
- **Numbers**: Press `1-13` for features
- **Shortcuts**: `m` (monitor), `l` (live), `w` (whales), `a` (analytics), `p` (portfolio), `e` (export), `s` (settings)
- **New shortcuts**: `arb` (arbitrage), `pred` (predictions), `wal` (wallets), `alert` (alerts), `ob` (orderbook)
- **Help**: Press `h` or `?`
- **Quit**: Press `q`

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
clob_endpoint = "wss://clob.polymarket.com/ws"

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
│   ├── predictions.py    # AI predictions
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
# Full test suite (184 tests)
pytest

# Specific test categories
pytest tests/test_core/ -v          # Core logic tests
pytest tests/test_db/ -v            # Database tests
pytest tests/test_cli/ -v           # CLI tests
pytest tests/test_tui/ -v           # TUI tests
pytest tests/test_live_data/ -v     # Live API tests
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

## Known Limitations

- **Portfolio tracking**: Limited due to Subgraph API deprecation (uses local trade history)
- **Individual trades**: WebSocket required for real-time individual trade data
- **Kalshi integration**: Requires Kalshi API key for cross-platform features

---

## Roadmap

### Completed in v0.4.0
- ✅ SQLite persistent database
- ✅ Individual whale/wallet tracking
- ✅ Insider detection engine
- ✅ Smart money identification
- ✅ Cross-market arbitrage scanner
- ✅ Kalshi cross-platform arbitrage
- ✅ Order book analysis with ASCII charts
- ✅ AI-powered predictions
- ✅ Market correlation engine
- ✅ Multi-channel notifications
- ✅ JSON output for all commands
- ✅ Historical data API

### Future
- 🔄 Python SDK for programmatic access
- 🔄 Custom dashboard builder
- 🔄 Webhook API for external integrations
- 🔄 News sentiment integration

---

## Support

- **Issues**: [GitHub Issues](https://github.com/NYTEMODEONLY/polyterm/issues)
- **Documentation**: See this README and inline `--help`
- **Updates**: `polyterm update` or `pipx upgrade polyterm`

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

**Built with ❤️ for the PolyMarket community**

*Your terminal window to prediction market alpha* 📊

*a [nytemode](https://nytemode.com) project*
