# Competitive Gap Analysis: PolyTerm vs Polymarket CLI

**Last updated:** 2026-02-25
**Competitor:** [Polymarket/polymarket-cli](https://github.com/Polymarket/polymarket-cli) (official)

---

## Executive Summary

Polymarket released their official CLI on Feb 24, 2026. It gained 1,016 GitHub stars in 24 hours. The tool is a Rust-based thin wrapper around their official SDK (`polymarket-client-sdk`), covering ~70 subcommands across market browsing, CLOB trading, wallet management, and on-chain operations.

**PolyTerm's position:** Analytics and intelligence platform. The official CLI is an API access layer. These serve different user segments, but the official CLI's market browsing overlaps with PolyTerm's entry-level use case and its "official" status creates gravitational pull.

**Key numbers:**
- Polymarket CLI: 70 subcommands, 0 analytics features, 0 visualizations, executes real trades
- PolyTerm: 84 CLI commands, 73+ TUI screens, 20+ analytics features, ASCII charts, no trade execution

---

## Current-State Comparison

### Feature Matrix

| Capability | PolyTerm (v0.8.5) | Polymarket CLI (v0.1.4) | Gap Owner |
|---|---|---|---|
| **Market browsing** | monitor, search, hot | markets list/get/search, events, tags, series | Parity |
| **Order book** | ASCII depth charts, iceberg detection, slippage calc | Full CLOB read (book, books, spreads, midpoints) | Polymarket CLI |
| **Price history** | DB snapshots, ASCII line/sparkline charts | CLOB price-history (1m/1h/6h/1d/1w/max intervals) | Polymarket CLI |
| **Trade execution** | None (links to Polymarket web) | Limit, market, batch, FOK, GTD, FAK, post-only | Polymarket CLI |
| **Wallet management** | View-only address tracking | Create, import, proxy, Gnosis Safe | Polymarket CLI |
| **On-chain ops** | None | CTF split/merge/redeem, contract approvals, bridge | Polymarket CLI |
| **Whale tracking** | Dedicated tracker + insider detection scoring | None | PolyTerm |
| **Arbitrage scanning** | Intra-market, correlated, cross-platform (Kalshi) | None | PolyTerm |
| **AI predictions** | 5-signal multi-factor (momentum, volume, whale, smart money, RSI) | None | PolyTerm |
| **Risk scoring** | 6-factor A-F grading system | None | PolyTerm |
| **Wash trade detection** | Volume quality indicators (4 metrics) | None | PolyTerm |
| **UMA dispute risk** | Resolution dispute analysis | None | PolyTerm |
| **Charts/visualization** | ASCII line, sparkline, bar, depth, comparison | Tables only | PolyTerm |
| **Position sizing** | Kelly Criterion calculator | None | PolyTerm |
| **Fee calculator** | Fee + slippage + gas estimation | Fee rate query only | PolyTerm |
| **Market comparison** | Side-by-side (up to 4 markets) | None | PolyTerm |
| **Bookmarks/favorites** | SQLite-backed with notes | None | PolyTerm |
| **Price alerts** | Direction-aware target alerts | None | PolyTerm |
| **Copy trading** | Follow up to 10 wallets with win rate tracking | None | PolyTerm |
| **Dashboard** | Overview of bookmarks, alerts, wallets | None | PolyTerm |
| **Calendar** | Upcoming resolutions with countdown | None | PolyTerm |
| **Statistics** | Volatility, RSI, trend, momentum | None | PolyTerm |
| **Parlay calculator** | Combined probability + EV + fee-adjusted payouts | None | PolyTerm |
| **P&L simulator** | Interactive profit/loss calculator | None | PolyTerm |
| **Trade journal** | Notes, reflections, streak tracking | None | PolyTerm |
| **Tutorial/glossary** | Interactive onboarding + terminology reference | None | PolyTerm |
| **TUI (interactive UI)** | 73+ screens, menu navigation, contextual help | None (readline REPL only) | PolyTerm |
| **Local database** | SQLite with 11 tables, auto-cleanup | JSON config file only | PolyTerm |
| **Notifications** | Telegram, Discord, desktop | None | PolyTerm |
| **JSON output** | All commands (`--format json`) | All commands (`-o json`) | Parity |
| **Leaderboard data** | Wallet leaderboard | Leaderboard + builder leaderboard | Polymarket CLI |
| **Comments/profiles** | None | View market comments, user profiles | Polymarket CLI |
| **Sports metadata** | None | NFL teams, market types | Polymarket CLI |
| **Reward tracking** | None | Rewards, earnings, order scoring | Polymarket CLI |
| **API key mgmt** | None | Create/delete CLOB API keys | Polymarket CLI |
| **Self-update** | PyPI check + auto-restart | `polymarket upgrade` + Homebrew | Polymarket CLI |
| **Install methods** | pip | Homebrew, curl script, cargo | Polymarket CLI |
| **Performance** | Python (~300ms startup) | Rust (native binary, ~10ms startup) | Polymarket CLI |
| **Test suite** | 440 tests | 40 integration tests | PolyTerm |

---

## Gap Analysis by Category

### 1. Core Trading Workflows

**Where they win:**
- Real trade execution (limit, market, batch orders with 4 order types)
- Full wallet lifecycle (create, import, proxy, Gnosis Safe)
- On-chain CTF operations (split, merge, redeem)
- Contract approval management
- Cross-chain bridge
- API key management for programmatic trading

**Where we win:**
- Trade preparation and analysis (quicktrade with P&L scenarios)
- Position sizing with Kelly Criterion
- Fee and slippage estimation before entry
- Exit strategy planning
- Parlay calculator for combined bets

**Gap assessment:** Their trading execution is a hard gap we should NOT close. PolyTerm's deliberate choice to not hold private keys is a trust/safety differentiator. Instead, we should make our pre-trade analysis so good that traders use PolyTerm to decide *what* to trade, then execute elsewhere.

### 2. Data Reliability

**Where they win:**
- Direct CLOB API access with 20+ pricing subcommands
- Official SDK integration (first-party data guarantees)
- Price history at 6 intervals (1m to max) from CLOB API
- Batch price queries
- Real-time tick size and fee rate data

**Where we win:**
- Multi-source aggregation (Gamma + CLOB fallback)
- Historical snapshot database (builds over time)
- Volume quality indicators (wash trade detection)
- Cross-platform data (Kalshi comparison)

**Gap assessment:** Our price history depends on accumulated snapshots (cold start problem). We should add CLOB price-history API support to provide instant historical data without requiring local accumulation.

### 3. UX

**Where they win:**
- Rust binary: instant startup (~10ms vs ~300ms)
- Homebrew + curl installer (broader reach than pip)
- Interactive shell (readline REPL)
- Clean error contract (stderr for tables, structured JSON errors)

**Where we win:**
- Full TUI with 73+ interactive screens and menu navigation
- Contextual tips and help system
- Interactive tutorial for onboarding
- Glossary for prediction market terminology
- Dashboard for at-a-glance overview
- Bookmarks, recent markets, notes
- ASCII charts and sparklines for visual analysis

**Gap assessment:** Our TUI is a massive UX advantage. Their REPL is basic readline. However, our Python startup time is noticeable. We should focus on making the TUI faster (lazy imports, caching) rather than trying to match Rust performance.

### 4. Automation / API Ergonomics

**Where they win:**
- All commands output structured JSON with `-o json`
- Every CLOB operation scriptable (create-order, cancel, batch)
- API key creation for bot development
- Being positioned for AI agent integration (GitHub issue #3)

**Where we win:**
- All commands support `--format json`
- Rich local database for stateful workflows
- Screener presets for saved queries
- Notification channels (Telegram, Discord) for automated alerts

**Gap assessment:** Both tools support JSON output. Their edge is trade execution scriptability. Our edge is stateful analytics pipelines. We should lean into automation of our analytics (scheduled scans, webhook triggers, pipeline composition).

### 5. Trust & Safety

**Where they win:**
- Official Polymarket product (brand trust)
- Built on official SDK (API compatibility guaranteed)
- Active maintenance by Polymarket engineer

**Where we win:**
- No private key handling (zero custody risk)
- Wash trade detection warns users about fake volume
- UMA dispute risk analysis warns about resolution uncertainty
- Risk scoring (A-F) helps users avoid bad markets
- Insider detection scoring flags suspicious wallets
- Fee transparency (breakeven, slippage, gas estimates)

**Gap assessment:** Their official status is unbeatable on brand trust. But they store private keys as plaintext (issue #18). Our no-custody approach is genuinely safer. We should make this a visible differentiator.

---

## Win Strategy

### Positioning: "Intelligence layer for Polymarket traders"

PolyTerm is not trying to be a thinner API wrapper. It is the analytics, risk management, and decision-support tool that makes traders better. The official CLI tells you what the prices are. PolyTerm tells you what the prices *mean*.

### Five Differentiators to Invest In

**1. Pre-Trade Intelligence Pipeline**
- Combine predictions + risk scoring + arbitrage + whale tracking into a unified "trade thesis" view
- Show: signal strength, risk grade, whale alignment, wash trade warnings, UMA dispute risk
- Target: Reduce trader research time from 15 minutes to 30 seconds per market
- Metric: Users who use PolyTerm before trading report higher win rates

**2. Terminal-Native Visualization**
- No other Polymarket tool has ASCII charts, sparklines, depth visualization
- Expand: add candlestick-style OHLC, volume profiles, multi-market overlay
- Target: Traders who want Bloomberg Terminal aesthetics without leaving the terminal
- Metric: Chart command usage, session length

**3. Risk Management Suite**
- No competitor has risk scoring, wash trade detection, UMA dispute risk, or insider detection
- Expand: portfolio-level risk aggregation, correlation-based diversification suggestions
- Target: Traders managing >$10k in positions who need risk guardrails
- Metric: Risk assessment usage before large trades

**4. Stateful Analytics (Local Database)**
- The official CLI is stateless (no local storage beyond wallet config)
- Our SQLite database enables: bookmarks, alerts, journals, position tracking, historical analysis
- Expand: trend detection over user's own trading history, personalized insights
- Target: Regular traders who use the tool daily
- Metric: Database row count growth, bookmark/alert creation rate

**5. Safety-First Approach**
- No private keys = no custody risk = no attack surface
- Wash trade warnings = informed decisions on volume quality
- Risk grades = accessible risk communication
- Target: Cautious traders, institutional researchers, regulators
- Metric: Zero security incidents, user trust in data quality

### What NOT to Build

- **Trade execution:** Don't compete with the official CLI on trading. Stay view-only. This is a feature, not a limitation.
- **Wallet management:** Don't handle private keys. Let users connect view-only addresses.
- **On-chain operations:** No CTF, no bridge, no approvals. Stay in the analytics layer.
- **Rust rewrite:** Python's rich ecosystem (Rich, numpy-style analytics) is our advantage. Optimize startup instead.

### Compounding Effect

These five differentiators compound: better intelligence (1) displayed through better visualization (2) with risk guardrails (3) tracked over time in a local database (4) with zero custody risk (5) creates a workflow that no single competing tool replicates. A trader using PolyTerm + the official CLI gets a better outcome than either tool alone.
