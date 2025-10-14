# PolyTerm 📊

A powerful, terminal-based monitoring tool for PolyMarket prediction markets. Track market shifts, whale activity, and trading opportunities—all from your command line with **100% live, verified 2025 data**.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Data](https://img.shields.io/badge/Data-Live%202025-brightgreen.svg)](API_SETUP.md)
[![PyPI](https://img.shields.io/badge/PyPI-polyterm-blue.svg)](https://pypi.org/project/polyterm/)

## 🚀 Quick Start

### Option 1: One-Command Install (Recommended)
```bash
curl -sSL https://raw.githubusercontent.com/NYTEMODEONLY/polyterm/main/install.sh | bash
```

### Option 2: Manual Install
```bash
# Clone and install
git clone https://github.com/NYTEMODEONLY/polyterm.git
cd polyterm
./install.sh
```

### Option 3: Direct from PyPI
```bash
pipx install polyterm
```

**That's it!** Now you can run PolyTerm from anywhere:
```bash
polyterm
```

## 🎨 Interactive Terminal Interface (TUI)

PolyTerm features a beautiful interactive menu for easy navigation:

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗  ██████╗ ██╗  ██╗   ██╗████████╗███████╗██████╗ ███╗   ███╗
║   ██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
║   ██████╔╝██║   ██║██║   ╚████╔╝    ██║   █████╗  ██████╔╝██╔████╔██║
║   ██╔═══╝ ██║   ██║██║    ╚██╔╝     ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
║   ██║     ╚██████╔╝███████╗██║      ██║   ███████╗██║  ██║██║ ╚═╝ ██║
║   ╚═╝      ╚═════╝ ╚══════╝╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝
║                                                           ║
║         Terminal-Based Monitoring for PolyMarket         ║
║                   Track. Analyze. Profit.                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────┐
│ 1  📊 Monitor Markets - Real-time market tracking
│ 2  🐋 Whale Activity - High-volume markets
│ 3  👁  Watch Market - Track specific market
│ 4  📈 Market Analytics - Trends and predictions
│ 5  💼 Portfolio - View your positions
│ 6  📤 Export Data - Export to JSON/CSV
│ 7  ⚙️  Settings - Configuration
│
│ h  ❓ Help - View documentation
│ q  🚪 Quit - Exit PolyTerm
└─────────────────────────────────────────────────┘
```

### Navigation
- **Numbers**: Press `1` through `7` for features
- **Letters**: `m` (monitor), `w` (whales), `a` (analytics), `p` (portfolio), `e` (export), `s` (settings)
- **Help**: Press `h` or `?`
- **Quit**: Press `q`

## 📊 Features

### 1. Real-Time Market Monitoring
Track live prediction markets with automatic updates:

```bash
polyterm monitor --limit 10
```

**What you'll see:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Market                                  ┃ Probability ┃ 24h Volume   ┃ Data Age ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ What price will Ethereum hit in 2025?  │      58.2% │   $203,519   │    45d   │
│ What price will Bitcoin hit in 2025?   │      42.1% │   $122,038   │    45d   │
│ Largest Company end of 2025?           │      31.5% │   $109,651   │    75d   │
│ How many Fed rate cuts in 2025?        │      28.9% │   $106,968   │    75d   │
└─────────────────────────────────────────┴────────────┴──────────────┴──────────┘
```

### 2. Whale Activity Detection
Identify high-volume markets (proxy for whale activity):

```bash
polyterm whales --hours 24 --min-amount 50000
```

**Output:**
```
High Volume Markets (Last 24h)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Market                               ┃ Trend ┃ Last Price ┃ 24h Volume ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Highest grossing movie in 2025?      │  NO   │     $0.073 │ $1,143,129 │
│ What price will Ethereum hit in 2025?│  NO   │     $0.180 │   $198,711 │
└──────────────────────────────────────┴───────┴────────────┴────────────┘
```

### 3. Market Watching & Alerts
Track specific markets with custom alerts:

```bash
polyterm watch <market-id> --threshold 5
```

### 4. Data Export
Export market data for analysis:

```bash
polyterm export --market <id> --format json
polyterm export --market <id> --format csv
```

### 5. Configuration Management
Customize PolyTerm settings:

```bash
polyterm config --list
polyterm config --set alerts.probability_threshold 10.0
polyterm config --set display.refresh_rate 5
```

## 🔧 Command Line Interface

For power users, all features are available via CLI commands:

```bash
# Monitor markets
polyterm monitor --limit 20 --refresh 3

# Track whale activity
polyterm whales --hours 48 --min-amount 100000

# Watch specific market
polyterm watch <market-id> --threshold 3 --interval 30

# Export data
polyterm export --market <id> --format json --output data.json

# Configuration
polyterm config --get api.gamma_base_url
polyterm config --set data_validation.min_volume_threshold 1000.0

# Portfolio (limited by API changes)
polyterm portfolio --wallet <address>

# Replay historical data
polyterm replay <market-id> --hours 24
```

## ⚙️ Configuration

PolyTerm stores configuration in `~/.polyterm/config.toml`:

```toml
[api]
gamma_base_url = "https://gamma-api.polymarket.com"
gamma_markets_endpoint = "/events"
clob_rest_endpoint = "https://clob.polymarket.com"
clob_endpoint = "wss://clob.polymarket.com/ws"

[data_validation]
max_market_age_hours = 24
require_volume_data = true
min_volume_threshold = 0.01
reject_closed_markets = true
enable_api_fallback = true

[alerts]
probability_threshold = 5.0
check_interval = 60

[display]
refresh_rate = 2
max_markets = 20
```

## 📡 Live Data Verification

PolyTerm uses **verified live 2025 data** from multiple sources:

### ✅ Working APIs (October 2025)
- **Gamma API** (`/events`): Primary source with volume data
- **CLOB API** (`/sampling-markets`): Fallback for current markets
- **Subgraph**: Enhanced filtering for on-chain data

### ❌ Deprecated APIs
- **Subgraph GraphQL**: Removed by The Graph (affects portfolio tracking)

### Data Validation
- ✅ All markets from 2025 or later
- ✅ Real trading volume data
- ✅ Active markets only
- ✅ Automatic freshness checks
- ✅ Multi-source fallback system

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Full test suite
pytest

# Live data tests
pytest tests/test_live_data/ -v

# TUI tests
pytest tests/test_tui/ -v

# All commands test
./test_all_commands.sh
```

## 📋 Known Limitations

### API-Level Constraints
1. **No Individual Trade Data**: PolyMarket APIs don't expose individual trades
   - Workaround: Volume-based whale detection

2. **No Portfolio History**: Subgraph API removed
   - Impact: Portfolio tracking unavailable
   - Workaround: None available (requires on-chain access)

3. **Limited Historical Data**: Gamma API provides snapshots
   - Impact: Replay command limited
   - Workaround: Uses available Gamma data

### What Still Works Perfectly
- ✅ Real-time market monitoring
- ✅ Live price and probability tracking
- ✅ Volume analysis
- ✅ Market discovery
- ✅ Custom alerts
- ✅ Data export
- ✅ Configuration management

## 🛠️ Development

### Setup Development Environment
```bash
git clone https://github.com/NYTEMODEONLY/polyterm.git
cd polyterm
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Run Tests
```bash
pytest
flake8 polyterm tests
```

### Build Package
```bash
python -m build
python -m twine upload dist/*
```

## 📚 Documentation

- **[TUI Guide](TUI_GUIDE.md)** - Complete Terminal User Interface guide
- **[API Setup](API_SETUP.md)** - API configuration and troubleshooting
- **[Contributing](CONTRIBUTING.md)** - How to contribute to PolyTerm
- **[Fixes Applied](FIXES_APPLIED.md)** - Complete summary of recent fixes
- **[Live Data Fix](LIVE_DATA_FIX_SUMMARY.md)** - Live data implementation details

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Steps
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit: `git commit -m "Add your feature"`
6. Push: `git push origin feature/your-feature`
7. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/NYTEMODEONLY/polyterm/issues)
- **API Status**: [PolyMarket Status](https://status.polymarket.com)
- **Documentation**: See docs/ directory

## 🎯 Roadmap

### Completed ✅
- ✅ Live 2025 data integration
- ✅ Interactive TUI with 8 screens
- ✅ Volume-based whale detection
- ✅ Multi-source API aggregation
- ✅ Comprehensive test suite
- ✅ PyPI package distribution

### Future Enhancements
- 🔄 Advanced analytics (correlations, predictions)
- 🔄 Market search functionality
- 🔄 Config editing UI
- 🔄 Real-time trade websocket integration
- 🔄 Alternative portfolio data sources

---

**Built with ❤️ for the PolyMarket community**

*Your terminal window to prediction markets* 📊