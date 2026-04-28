# PolyTerm Documentation

> Comprehensive documentation for PolyTerm — a terminal-based monitoring and analytics tool for Polymarket prediction markets.

## Quick Start

```bash
pip install polyterm
polyterm              # Launch TUI
polyterm tutorial     # Interactive tutorial
polyterm --help       # See all commands
```

## Table of Contents

### CLI Commands

Each CLI command has its own documentation page with usage, options, and examples.

| Command | Description | Doc |
|---------|-------------|-----|
| [center](cli/center.md) | Alert center management | `polyterm center` |
| [alerts](cli/alerts.md) | Alert configuration and management | `polyterm alerts` |
| [analyze](cli/analyze.md) | Market analytics and trending | `polyterm analyze` |
| [arbitrage](cli/arbitrage.md) | Arbitrage opportunity scanner | `polyterm arbitrage` |
| [attribution](cli/attribution.md) | Trade attribution analysis | `polyterm attribution` |
| [backtest](cli/backtest.md) | Strategy backtesting | `polyterm backtest` |
| [benchmark](cli/benchmark.md) | Performance benchmarking | `polyterm benchmark` |
| [bookmarks](cli/bookmarks.md) | Save and manage favorite markets | `polyterm bookmarks` |
| [calendar](cli/calendar.md) | Upcoming market resolutions | `polyterm calendar` |
| [calibrate](cli/calibrate.md) | Prediction calibration analysis | `polyterm calibrate` |
| [chart](cli/chart.md) | ASCII price history charts | `polyterm chart` |
| [clusters](cli/clusters.md) | Wallet cluster detection | `polyterm clusters` |
| [compare](cli/compare.md) | Compare markets side by side | `polyterm compare` |
| [config](cli/config.md) | Configuration management | `polyterm config` |
| [correlate](cli/correlate.md) | Market correlation analysis | `polyterm correlate` |
| [crypto15m](cli/crypto15m.md) | 15-minute crypto prediction markets | `polyterm crypto15m` |
| [dashboard](cli/dashboard.md) | Quick activity overview | `polyterm dashboard` |
| [depth](cli/depth.md) | Order book depth analysis | `polyterm depth` |
| [digest](cli/digest.md) | Market digest / summary report | `polyterm digest` |
| [ev](cli/ev.md) | Expected value calculator | `polyterm ev` |
| [exit](cli/exit.md) | Exit plan calculator | `polyterm exit` |
| [export](cli/export.md) | Data export utilities | `polyterm export` |
| [fees](cli/fees.md) | Fee and slippage calculator | `polyterm fees` |
| [follow](cli/follow.md) | Copy trading / wallet following | `polyterm follow` |
| [glossary](cli/glossary.md) | Prediction market terminology | `polyterm glossary` |
| [groups](cli/groups.md) | Market grouping and organization | `polyterm groups` |
| [health](cli/health.md) | Market health indicators | `polyterm health` |
| [history](cli/history.md) | Trade and price history | `polyterm history` |
| [hot](cli/hot.md) | Hot / trending markets | `polyterm hot` |
| [journal](cli/journal.md) | Trading journal | `polyterm journal` |
| [ladder](cli/ladder.md) | Price ladder display | `polyterm ladder` |
| [leaderboard](cli/leaderboard.md) | Trader leaderboard | `polyterm leaderboard` |
| [liquidity](cli/liquidity.md) | Liquidity analysis | `polyterm liquidity` |
| [live-monitor](cli/live-monitor.md) | Real-time WebSocket market monitor | `polyterm live-monitor` |
| [lookup](cli/lookup.md) | Market lookup by ID or slug | `polyterm lookup` |
| [monitor](cli/monitor.md) | Market monitoring with polling | `polyterm monitor` |
| [mywallet](cli/mywallet.md) | View-only wallet connection | `polyterm mywallet` |
| [negrisk](cli/negrisk.md) | NegRisk multi-outcome arbitrage | `polyterm negrisk` |
| [news](cli/news.md) | Market-relevant news headlines | `polyterm news` |
| [notes](cli/notes.md) | Market notes management | `polyterm notes` |
| [notify](cli/notify.md) | Notification configuration | `polyterm notify` |
| [odds](cli/odds.md) | Odds format converter | `polyterm odds` |
| [orderbook](cli/orderbook.md) | Order book analysis (REST + live WS) | `polyterm orderbook` |
| [parlay](cli/parlay.md) | Parlay bet calculator | `polyterm parlay` |
| [pin](cli/pin.md) | Pin markets for quick access | `polyterm pin` |
| [pnl](cli/pnl.md) | Profit and loss tracking | `polyterm pnl` |
| [portfolio](cli/portfolio.md) | Portfolio overview | `polyterm portfolio` |
| [position](cli/position.md) | Position tracking and management | `polyterm position` |
| [predict](cli/predict.md) | Signal-based predictions | `polyterm predict` |
| [presets](cli/presets.md) | Screener preset management | `polyterm presets` |
| [pricealert](cli/pricealert.md) | Price target alerts | `polyterm pricealert` |
| [quick](cli/quick.md) | Quick market overview | `polyterm quick` |
| [quicktrade](cli/quicktrade.md) | Trade preparation with direct links | `polyterm quicktrade` |
| [recent](cli/recent.md) | Recently viewed markets | `polyterm recent` |
| [replay](cli/replay.md) | Market replay and analysis | `polyterm replay` |
| [report](cli/report.md) | Generate market reports | `polyterm report` |
| [rewards](cli/rewards.md) | Holding and liquidity rewards | `polyterm rewards` |
| [risk](cli/risk.md) | Market risk assessment (A-F grades) | `polyterm risk` |
| [scenario](cli/scenario.md) | Scenario analysis | `polyterm scenario` |
| [screener](cli/screener.md) | Market screener with filters | `polyterm screener` |
| [search](cli/search.md) | Advanced market search | `polyterm search` |
| [sentiment](cli/sentiment.md) | Market sentiment analysis | `polyterm sentiment` |
| [signals](cli/signals.md) | Trading signal analysis | `polyterm signals` |
| [similar](cli/similar.md) | Find similar markets | `polyterm similar` |
| [simulate](cli/simulate.md) | P&L simulation calculator | `polyterm simulate` |
| [size](cli/size.md) | Position size calculator (Kelly Criterion) | `polyterm size` |
| [snapshot](cli/snapshot.md) | Market snapshot capture | `polyterm snapshot` |
| [spread](cli/spread.md) | Spread analysis | `polyterm spread` |
| [stats](cli/stats.md) | Market statistics and technicals | `polyterm stats` |
| [streak](cli/streak.md) | Win/loss streak tracking | `polyterm streak` |
| [summary](cli/summary.md) | Market summary generation | `polyterm summary` |
| [timeline](cli/timeline.md) | Market event timeline | `polyterm timeline` |
| [timing](cli/timing.md) | Trade timing analysis | `polyterm timing` |
| [trade](cli/trade.md) | Trade management | `polyterm trade` |
| [tutorial](cli/tutorial.md) | Interactive tutorial for new users | `polyterm tutorial` |
| [update](cli/update.md) | Check for and install updates | `polyterm update` |
| [volume](cli/volume.md) | Volume analysis | `polyterm volume` |
| [wallets](cli/wallets.md) | Wallet management and analysis | `polyterm wallets` |
| [watch](cli/watch.md) | Market watchlist | `polyterm watch` |
| [watchdog](cli/watchdog.md) | Market watchdog monitoring | `polyterm watchdog` |
| [whales](cli/whales.md) | Whale activity tracker | `polyterm whales` |

### TUI Screens

Each TUI screen is documented with navigation, keyboard shortcuts, and data sources.

| Screen | Description | Shortcut | Doc |
|--------|-------------|----------|-----|
| [alertcenter_screen](tui/screens/alertcenter_screen.md) | Alert center dashboard | - | TUI |
| [alerts_screen](tui/screens/alerts_screen.md) | Alert configuration | 12/alert | TUI |
| [analytics](tui/screens/analytics.md) | Market analytics display | 5/a | TUI |
| [analyze_screen](tui/screens/analyze_screen.md) | Deep market analysis | an | TUI |
| [arbitrage](tui/screens/arbitrage.md) | Arbitrage opportunities | 9/arb | TUI |
| [attribution_screen](tui/screens/attribution_screen.md) | Trade attribution | - | TUI |
| [backtest_screen](tui/screens/backtest_screen.md) | Strategy backtesting | - | TUI |
| [benchmark_screen](tui/screens/benchmark_screen.md) | Performance benchmark | - | TUI |
| [bookmarks_screen](tui/screens/bookmarks_screen.md) | Saved markets | 17/bm | TUI |
| [calendar_screen](tui/screens/calendar_screen.md) | Resolution calendar | cal | TUI |
| [calibrate_screen](tui/screens/calibrate_screen.md) | Calibration analysis | - | TUI |
| [chart_screen](tui/screens/chart_screen.md) | Price charts | ch | TUI |
| [clusters_screen](tui/screens/clusters_screen.md) | Wallet clusters | cl | TUI |
| [compare_screen](tui/screens/compare_screen.md) | Market comparison | cmp | TUI |
| [correlate_screen](tui/screens/correlate_screen.md) | Correlation analysis | corr | TUI |
| [crypto15m_screen](tui/screens/crypto15m_screen.md) | 15-min crypto markets | c15 | TUI |
| [dashboard_screen](tui/screens/dashboard_screen.md) | Activity dashboard | d | TUI |
| [depth_screen](tui/screens/depth_screen.md) | Order book depth | dp | TUI |
| [digest_screen](tui/screens/digest_screen.md) | Market digest | - | TUI |
| [ev_screen](tui/screens/ev_screen.md) | Expected value | - | TUI |
| [exit_screen](tui/screens/exit.md) | Exit plan | ex | TUI |
| [export](tui/screens/export.md) | Data export | 7/e | TUI |
| [fees_screen](tui/screens/fees.md) | Fee calculator | fee | TUI |
| [follow_screen](tui/screens/follow.md) | Copy trading | 15/follow | TUI |
| [glossary_screen](tui/screens/glossary.md) | Glossary | g | TUI |
| [groups_screen](tui/screens/groups.md) | Market groups | - | TUI |
| [health_screen](tui/screens/health.md) | Market health | - | TUI |
| [help](tui/screens/help.md) | Help screen | h/? | TUI |
| [history_screen](tui/screens/history.md) | Trade history | - | TUI |
| [hot_screen](tui/screens/hot.md) | Hot markets | hot | TUI |
| [journal_screen](tui/screens/journal_screen.md) | Trading journal | jn | TUI |
| [ladder_screen](tui/screens/ladder_screen.md) | Price ladder | - | TUI |
| [leaderboard_screen](tui/screens/leaderboard_screen.md) | Trader leaderboard | - | TUI |
| [liquidity_screen](tui/screens/liquidity_screen.md) | Liquidity analysis | - | TUI |
| [live_monitor](tui/screens/live_monitor.md) | Live WebSocket monitor | 2/l | TUI |
| [market_picker](tui/screens/market_picker.md) | Market selection dialog | - | TUI |
| [monitor](tui/screens/monitor.md) | Market monitor | 1/m | TUI |
| [mywallet_screen](tui/screens/mywallet_screen.md) | My wallet | mw | TUI |
| [negrisk_screen](tui/screens/negrisk_screen.md) | NegRisk arbitrage | nr | TUI |
| [news_screen](tui/screens/news_screen.md) | News headlines | nw | TUI |
| [notes](tui/screens/notes.md) | Market notes | nt | TUI |
| [notify_screen](tui/screens/notify_screen.md) | Notifications | - | TUI |
| [odds_screen](tui/screens/odds_screen.md) | Odds converter | - | TUI |
| [orderbook_screen](tui/screens/orderbook_screen.md) | Order book (live) | 13/ob | TUI |
| [parlay_screen](tui/screens/parlay_screen.md) | Parlay calculator | 16/parlay | TUI |
| [pin_screen](tui/screens/pin_screen.md) | Pinned markets | - | TUI |
| [pnl_screen](tui/screens/pnl_screen.md) | Profit/loss | pnl | TUI |
| [portfolio](tui/screens/portfolio.md) | Portfolio view | 6/p | TUI |
| [position_screen](tui/screens/position_screen.md) | Position tracker | pos | TUI |
| [predictions](tui/screens/predictions.md) | Predictions | 10/pred | TUI |
| [presets_screen](tui/screens/presets_screen.md) | Screener presets | pr | TUI |
| [pricealert_screen](tui/screens/pricealert_screen.md) | Price alerts | pa | TUI |
| [quick_screen](tui/screens/quick_screen.md) | Quick update | u | TUI |
| [quicktrade_screen](tui/screens/quicktrade_screen.md) | Quick trade | qt | TUI |
| [recent_screen](tui/screens/recent_screen.md) | Recent markets | rec | TUI |
| [report_screen](tui/screens/report_screen.md) | Reports | - | TUI |
| [rewards_screen](tui/screens/rewards_screen.md) | Rewards estimates | rw | TUI |
| [risk_screen](tui/screens/risk_screen.md) | Risk assessment | 14/risk | TUI |
| [scenario_screen](tui/screens/scenario_screen.md) | Scenario analysis | - | TUI |
| [screener_screen](tui/screens/screener_screen.md) | Market screener | sr | TUI |
| [search_screen](tui/screens/search_screen.md) | Advanced search | sr | TUI |
| [sentiment_screen](tui/screens/sentiment_screen.md) | Sentiment analysis | sent | TUI |
| [settings](tui/screens/settings.md) | Settings | 8/s | TUI |
| [signals_screen](tui/screens/signals_screen.md) | Trading signals | - | TUI |
| [similar_screen](tui/screens/similar_screen.md) | Similar markets | - | TUI |
| [simulate_screen](tui/screens/simulate_screen.md) | P&L simulator | sim | TUI |
| [size_screen](tui/screens/size_screen.md) | Position size calc | sz | TUI |
| [snapshot_screen](tui/screens/snapshot_screen.md) | Market snapshot | - | TUI |
| [spread_screen](tui/screens/spread_screen.md) | Spread analysis | - | TUI |
| [stats_screen](tui/screens/stats_screen.md) | Market statistics | st | TUI |
| [streak_screen](tui/screens/streak_screen.md) | Win/loss streaks | - | TUI |
| [timeline_screen](tui/screens/timeline_screen.md) | Event timeline | tl | TUI |
| [timing_screen](tui/screens/timing_screen.md) | Trade timing | - | TUI |
| [trade_screen](tui/screens/trade_screen.md) | Trade management | tr | TUI |
| [tutorial_screen](tui/screens/tutorial_screen.md) | Tutorial | t | TUI |
| [volume_screen](tui/screens/volume_screen.md) | Volume analysis | - | TUI |
| [wallets](tui/screens/wallets.md) | Wallet management | 11/wal | TUI |
| [watch](tui/screens/watch.md) | Watchlist | 4 | TUI |
| [watchdog_screen](tui/screens/watchdog_screen.md) | Market watchdog | - | TUI |
| [whales](tui/screens/whales.md) | Whale tracker | 3/w | TUI |

### TUI Infrastructure

| Module | Description | Doc |
|--------|-------------|-----|
| [controller](tui/infrastructure/controller.md) | Main TUI loop and routing | `TUIController` |
| [menu](tui/infrastructure/menu.md) | Main menu with update checking | Menu display |
| [shortcuts](tui/infrastructure/shortcuts.md) | Keyboard shortcut mapping | Shortcut registry |
| [statusbar](tui/infrastructure/statusbar.md) | Status bar display | Status info |
| [themes](tui/infrastructure/themes.md) | Color themes and styling | Theme config |
| [logo](tui/infrastructure/logo.md) | ASCII logo display | Branding |

### API Modules

| Module | Description | Doc |
|--------|-------------|-----|
| [aggregator](api/aggregator.md) | Multi-source data aggregation with fallback | Primary data layer |
| [clob](api/clob.md) | CLOB REST + WebSocket (order book, trades, settlement) | Real-time data |
| [data_api](api/data_api.md) | Data API client (wallet positions, activity) | Wallet data |
| [gamma](api/gamma.md) | Gamma REST API + SharedRateLimiter | Market data |
| [subgraph](api/subgraph.md) | Subgraph client (legacy) | Historical data |

### Core Modules

| Module | Description | Doc |
|--------|-------------|-----|
| [alerts](core/alerts.md) | Alert generation and management | Alert engine |
| [analytics](core/analytics.md) | Market analytics and trending analysis | Analytics engine |
| [arbitrage](core/arbitrage.md) | Intra-market, correlated, and cross-platform arbitrage | Arb scanner |
| [charts](core/charts.md) | ASCII chart generation (line, bar, sparkline) | Visualization |
| [cluster_detector](core/cluster_detector.md) | Wallet cluster detection (same-entity analysis) | Cluster analysis |
| [correlation](core/correlation.md) | Market correlation analysis | Correlation engine |
| [fees](core/fees.md) | CLOB V2 fee schedule parsing and protocol fee estimates | Fee model |
| [historical](core/historical.md) | Historical data management | Data history |
| [negrisk](core/negrisk.md) | NegRisk multi-outcome arbitrage detection | NegRisk arb |
| [news](core/news.md) | RSS news aggregation engine | News feeds |
| [notifications](core/notifications.md) | Multi-channel notifications (Telegram, Discord, email) | Notification dispatch |
| [orderbook](core/orderbook.md) | Order book analysis + LiveOrderBook WebSocket | Order book engine |
| [portfolio](core/portfolio.md) | Portfolio tracking and analysis | Portfolio engine |
| [predictions](core/predictions.md) | Multi-factor signal-based predictions | Prediction engine |
| [rewards](core/rewards.md) | Holding and liquidity rewards calculator | Rewards estimator |
| [risk_score](core/risk_score.md) | Market risk scoring (A-F grades, 6 factors) | Risk engine |
| [scanner](core/scanner.md) | Market monitoring and shift detection | Market scanner |
| [uma_tracker](core/uma_tracker.md) | UMA oracle dispute risk analysis | Dispute tracking |
| [wash_trade_detector](core/wash_trade_detector.md) | Wash trade detection indicators | Volume quality |
| [whale_tracker](core/whale_tracker.md) | Whale tracking + insider detection | Whale engine |

### Database Layer

| Module | Description | Doc |
|--------|-------------|-----|
| [database](db/database.md) | SQLite database manager (11 tables, auto-migration) | Data persistence |
| [models](db/models.md) | Data models (Wallet, Trade, Alert, MarketSnapshot, etc.) | Data structures |

### Utilities

| Module | Description | Doc |
|--------|-------------|-----|
| [config](utils/config.md) | TOML-based configuration management | `~/.polyterm/config.toml` |
| [errors](utils/errors.md) | Centralized user-friendly error handling | Error display |
| [formatting](utils/formatting.md) | Terminal output formatting utilities | Display helpers |
| [json_output](utils/json_output.md) | JSON serialization for `--format json` | Scripting interface |
| [tips](utils/tips.md) | Context-specific tips and hints | Beginner guidance |
| [contextual_help](utils/contextual_help.md) | Screen-specific help content | Help system |

## Architecture Overview

```
polyterm/
├── api/              # Data layer - API clients
├── core/             # Business logic engines
├── db/               # SQLite persistence
├── cli/              # Click-based CLI commands
├── tui/              # Terminal UI (Rich-based)
└── utils/            # Shared utilities
```

**Data Flow**: API clients fetch data → Core modules process/analyze → CLI commands display results → TUI screens provide interactive access.

**Key Patterns**:
- **API Fallback**: `APIAggregator` tries Gamma API first, falls back to CLOB
- **TUI → CLI**: Most TUI screens launch CLI commands via subprocess
- **WebSocket**: Live monitor uses RTDS WebSocket with polling fallback
- **Config**: TOML-based at `~/.polyterm/config.toml` with dot notation access
- **Database**: SQLite at `~/.polyterm/data.db` with context manager pattern

## Global Features

All CLI commands support:
- `--format json` — JSON output for scripting and automation
- `--help` — Command-specific help
- Rich terminal formatting with color and tables

## Contributing

When adding new features, create a corresponding documentation page following the [template](TEMPLATE.md) and add it to this index.
