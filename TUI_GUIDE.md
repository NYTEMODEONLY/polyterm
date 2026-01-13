# PolyTerm TUI Guide

Complete guide to using PolyTerm's Terminal User Interface.

## Table of Contents

- [Getting Started](#getting-started)
- [Main Menu](#main-menu)
- [Core Features](#core-features)
- [Premium Features](#premium-features)
- [Tools & Calculators](#tools--calculators)
- [Research & Analysis](#research--analysis)
- [Learning Resources](#learning-resources)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Tips & Tricks](#tips--tricks)

## Getting Started

Launch the TUI with:

```bash
polyterm
```

**First-time users** will be guided through an interactive tutorial covering:
- How prediction markets work
- Understanding prices and probabilities
- Tracking whales and smart money
- Finding arbitrage opportunities

You can skip the tutorial and access it anytime by pressing `t`.

## Main Menu

The main menu displays all available features with keyboard shortcuts:

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

### Navigation

- **Numbers**: Press `1-17` for numbered features
- **Shortcuts**: Use letter/abbreviation shortcuts (e.g., `m` for monitor)
- **Help**: Press `h` or `?`
- **Tutorial**: Press `t` for the interactive tutorial
- **Glossary**: Press `g` for terminology
- **Quick Update**: Press `u` when an update is available
- **Quit**: Press `q`

### Version Display & Updates

PolyTerm automatically checks for updates on launch:

**Current Version:**
```
Main Menu
PolyTerm v0.5.2
```

**Update Available:**
```
Main Menu
PolyTerm v0.5.2 Update Available: v0.5.3
```

Press `u` to quick update directly from the menu.

## Core Features

### 1. Monitor Markets (1/m)

Real-time market tracking with live probability updates.

**Prompts:**
- How many markets to display?
- Category filter (politics/crypto/sports)
- Refresh rate in seconds
- Active markets only?
- Show volume quality indicators?

**Features:**
- Live-updating table of markets
- Color-coded changes (green=up, red=down)
- Volume quality indicators (wash trade detection)
- Press `Ctrl+C` to stop

### 2. Live Monitor (2/l)

Dedicated terminal window for focused real-time monitoring.

### 3. Whale Activity (3/w)

Track high-volume markets and whale activity.

**Prompts:**
- Minimum 24hr volume
- Lookback period in hours
- Maximum results

### 4. Watch Market (4)

Track a specific market with custom alerts.

**Prompts:**
- Search for market or enter Market ID
- Alert threshold percentage
- Check interval

### 5. Market Analytics (5/a)

Advanced market analysis including:
- Trending markets
- Market correlations
- Volume analysis

### 6. Portfolio (6/p)

View your positions and P&L tracking.

### 7. Export Data (7/e)

Export market data to JSON or CSV formats.

### 8. Settings (8/s)

Configure PolyTerm settings:
- Alert thresholds
- API settings
- Display preferences
- Notification channels
- Update PolyTerm

## Premium Features

### 9. Arbitrage Scanner (9/arb)

Find cross-market profit opportunities.

**Types detected:**
- **Intra-market**: YES + NO < $1.00
- **Correlated**: Similar events with price gaps
- **Cross-platform**: Polymarket vs Kalshi

### 10. Predictions (10/pred)

Signal-based market predictions using:
- Price momentum
- Volume acceleration
- Whale behavior
- Smart money positioning
- Technical indicators (RSI)

### 11. Wallets (11/wal)

Smart money tracking:
- Whale wallets (by volume)
- Smart money (>70% win rate)
- Suspicious wallets (insider risk scoring)
- Analyze specific wallets

### 12. Alerts (12/alert)

Multi-channel notification management:
- View recent alerts
- Filter by type (whale, insider, arbitrage)
- Test Telegram/Discord notifications
- Acknowledge alerts

### 13. Order Book (13/ob)

Analyze market depth:
- ASCII depth charts
- Slippage calculations
- Large order detection (icebergs)
- Support/resistance levels

### 14. Risk Assessment (14/risk)

Market risk scoring (A-F grades) based on:
- Resolution clarity (25%)
- Liquidity (20%)
- Time risk (15%)
- Volume quality (15%)
- Spread (15%)
- Category risk (10%)

### 15. Copy Trading (15/follow)

Follow successful wallets:
- Track up to 10 wallets
- View win rates and stats
- Get alerts on their trades

### 16. Parlay Calculator (16/parlay)

Combine multiple bets:
- Calculate combined probability
- View decimal/American odds
- Expected value analysis
- Fee-adjusted payouts

### 17. Bookmarks (17/bm)

Save favorite markets:
- Quick access to watched markets
- Add notes to bookmarks
- Interactive management

## Tools & Calculators

### Dashboard (d)

Quick overview showing:
- Top volume markets
- Your bookmarks
- Active alerts
- Followed wallet activity

### Simulate P&L (sim)

Interactive profit/loss calculator for scenario analysis.

### Position Size Calculator (sz)

Kelly Criterion-based bet sizing:
- Calculate optimal position size
- Full vs fractional Kelly
- Edge and expected value

### Fee Calculator (fee)

Calculate trading costs:
- Polymarket fee structure
- Slippage estimation
- Net profit projections
- Gas fee estimates

### Price Alerts (pa)

Set target price notifications:
- Alert when price crosses threshold
- Direction-aware (above/below)
- Persistent across sessions

### Market Calendar (cal)

View upcoming market resolutions:
- Filter by days ahead
- Filter by category
- See resolution countdown

## Research & Analysis

### Price Charts (ch)

ASCII price history visualization:
- Line charts
- Sparklines for compact display
- Customizable timeframe

### Compare Markets (cmp)

Side-by-side market comparison:
- Compare up to 4 markets
- See price changes and volumes
- Identify arbitrage opportunities

### Market Statistics (st)

Technical analysis:
- Volatility (standard deviation)
- Trend analysis (regression)
- RSI indicator
- Momentum detection

### Advanced Search (sr)

Filter markets by:
- Category
- Volume/liquidity
- Price range
- Resolution date

### Recent Markets (rec)

Quick return to recently viewed markets with view counts.

### Market Notes (nt)

Add personal notes to markets for tracking your analysis.

## Learning Resources

### Tutorial (t)

Interactive beginner guide covering:
- Prediction market basics
- Price = probability concept
- Whale tracking
- Arbitrage fundamentals

### Glossary (g)

Comprehensive prediction market terminology reference.

## Keyboard Shortcuts

### Quick Reference

| Key(s) | Action |
|--------|--------|
| `1-17` | Numbered menu items |
| `m` | Monitor Markets |
| `l` | Live Monitor |
| `w` | Whale Activity |
| `a` | Analytics |
| `p` | Portfolio |
| `e` | Export |
| `s` | Settings |
| `d` | Dashboard |
| `t` | Tutorial |
| `g` | Glossary |
| `sim` | Simulate P&L |
| `arb` | Arbitrage |
| `pred` | Predictions |
| `wal` | Wallets |
| `ob` | Order Book |
| `risk` | Risk Assessment |
| `follow` | Copy Trading |
| `parlay` | Parlay Calculator |
| `bm` | Bookmarks |
| `ch` | Chart |
| `cmp` | Compare |
| `sz` | Size Calculator |
| `rec` | Recent |
| `pa` | Price Alerts |
| `cal` | Calendar |
| `fee` | Fee Calculator |
| `st` | Stats |
| `sr` | Search |
| `hot` | Hot Markets |
| `pnl` | Profit/Loss |
| `u` | Quick Update |
| `h`, `?` | Help |
| `q` | Quit |

### Global Controls

| Key | Action |
|-----|--------|
| `Ctrl+C` | Stop current operation |
| `Enter` | Return to main menu |

## Tips & Tricks

### Quick Workflow

1. Start with **Dashboard** (`d`) for a quick overview
2. Use **Monitor** (`m`) to see top markets
3. **Bookmark** (`bm`) interesting markets
4. Set **Price Alerts** (`pa`) for notifications
5. Check **Calendar** (`cal`) for upcoming resolutions

### Power User Mode

Use CLI commands directly for scripting:

```bash
# JSON output for automation
polyterm monitor --format json --limit 10 --once | jq '.markets[]'

# Arbitrage scanning
polyterm arbitrage --format json | jq '.opportunities[]'

# Predictions
polyterm predict --format json --min-confidence 0.7
```

### Configuration

Edit `~/.polyterm/config.toml` for persistent settings:

```toml
[alerts]
probability_threshold = 5.0
check_interval = 60

[display]
refresh_rate = 2
max_markets = 20

[notification.telegram]
enabled = true
bot_token = "YOUR_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"
```

### Troubleshooting

**TUI not launching?**
```bash
pip show polyterm
pip install --upgrade polyterm
```

**Want CLI only?**
```bash
polyterm monitor  # Skips TUI, runs directly
polyterm whales   # Skips TUI, runs directly
```

## Getting Help

- Press `h` in the TUI for quick help
- See [README.md](README.md) for full documentation
- Check [API_SETUP.md](API_SETUP.md) for API details
- Report issues: [GitHub Issues](https://github.com/NYTEMODEONLY/polyterm/issues)

---

**Enjoy using PolyTerm!**

*Your terminal window to prediction markets*
