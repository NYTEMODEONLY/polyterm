# PolyTerm Implementation Checklist

> Actionable tasks to make PolyTerm the go-to tool for prediction market traders.

---

## Immediate Priority: Beginner Experience (v0.5.0)

### Tutorial System - COMPLETED
- [x] Create `polyterm/cli/commands/tutorial.py`
  - [x] Interactive walkthrough of main features (8 steps)
  - [x] Step-by-step market monitoring demo
  - [x] Explain price = probability concept
  - [x] Show how to set up alerts
  - [x] Uses Rich panels and prompts

- [x] Add to TUI menu as option `t/tutorial`
- [x] First-run detection in `controller.py`
  - [x] Check `~/.polyterm/.onboarded` flag
  - [x] Prompt to run tutorial if not onboarded

### Position Simulator - COMPLETED (NEW)
- [x] Create `polyterm/cli/commands/simulate.py`
  - [x] Interactive P&L calculator
  - [x] Shows max profit, max loss, ROI
  - [x] Exit price scenarios
  - [x] Fee calculations
- [x] Add to TUI menu as option `sim/simulate`
- [x] Created tips system `polyterm/utils/tips.py`

### Glossary Command - COMPLETED
- [x] Create `polyterm/cli/commands/glossary.py`
  - [x] 30+ terms across 7 categories
  - [x] Rich table with term + definition
  - [x] Search functionality: `polyterm glossary --search <term>`
  - [x] Category filtering: `polyterm glossary --category <name>`

### Contextual Help System
- [ ] Add `?` key handler to TUI controller
  - [ ] Show help panel for current screen
  - [ ] List available actions
  - [ ] Explain displayed metrics

- [ ] Create help content for each screen:
  - [ ] Monitor: Explain columns (prob, volume, change)
  - [ ] Whales: Explain what constitutes a whale
  - [ ] Arbitrage: Explain spread calculations
  - [ ] Predictions: Explain signal types
  - [ ] Orderbook: Explain bid/ask, spread, depth

### Better Error Messages
- [ ] Audit all `except` blocks for user-friendly messages
- [ ] Add suggestions for common errors:
  - [ ] Network errors: "Check your internet connection"
  - [ ] API errors: "Polymarket API may be down, try again later"
  - [ ] Config errors: "Run 'polyterm config' to fix settings"

---

## High Impact: Market Intelligence (v0.6.0)

### UMA Dispute Tracker
- [ ] Research UMA contract addresses on Polygon
- [ ] Create `polyterm/api/uma.py`
  - [ ] Fetch active disputes
  - [ ] Get voting status
  - [ ] Track dispute history

- [ ] Create `polyterm/cli/commands/disputes.py`
  - [ ] List active disputes
  - [ ] Show market affected
  - [ ] Display vote counts
  - [ ] Show time remaining

- [ ] Create `polyterm/tui/screens/disputes_screen.py`
- [ ] Add alert type: `dispute_started`
- [ ] Add `--disputes` flag to watch command

### Wash Trade Detection
- [ ] Create `polyterm/core/wash_detector.py`
  - [ ] Track rapid buy-sell patterns
  - [ ] Identify same-address trades
  - [ ] Calculate wash volume percentage
  - [ ] Return "real volume" estimate

- [ ] Add to market monitor display:
  - [ ] `[W]` indicator for suspected wash trading
  - [ ] Optional `--real-volume` column

- [ ] Add `polyterm analyze --market X --wash-check`

### Market Risk Score
- [ ] Create scoring algorithm in `polyterm/core/risk_score.py`
  - [ ] Factor: Rule clarity (subjective vs objective)
  - [ ] Factor: Historical dispute rate
  - [ ] Factor: Time to resolution
  - [ ] Factor: Liquidity depth
  - [ ] Factor: Wash trade percentage
  - [ ] Return A-F grade

- [ ] Display risk score in market details
- [ ] Add `--min-risk-grade` filter to monitor

---

## Social Features (v0.7.0)

### Copy Trading / Wallet Following
- [ ] Add `followed_wallets` table to database
- [ ] Commands:
  - [ ] `polyterm wallets --follow 0xABC`
  - [ ] `polyterm wallets --unfollow 0xABC`
  - [ ] `polyterm wallets --following` (list followed)

- [ ] Alert when followed wallet trades:
  - [ ] New alert type: `followed_wallet_trade`
  - [ ] Include: wallet, market, direction, size

- [ ] TUI screen for managing followed wallets

### Performance Leaderboard
- [ ] Calculate ROI for tracked wallets
- [ ] `polyterm leaderboard` command
  - [ ] Top 20 wallets by ROI
  - [ ] Filter by time period
  - [ ] Show win rate, volume, avg position

### Parlay Calculator
- [ ] Create `polyterm/cli/commands/parlay.py`
- [ ] Input: multiple market IDs
- [ ] Output: combined probability, max payout
- [ ] What-if scenarios for different outcomes

---

## Professional Tools (v0.8.0)

### Python SDK
- [ ] Create `polyterm-sdk` package
- [ ] Classes:
  - [ ] `PolyTerm` - main client
  - [ ] `Market` - market data model
  - [ ] `Wallet` - wallet tracking
  - [ ] `Alert` - alert configuration

- [ ] Methods:
  - [ ] `get_markets()`
  - [ ] `get_whale_activity()`
  - [ ] `get_arbitrage_opportunities()`
  - [ ] `subscribe_alerts(callback)`

### Webhook API
- [ ] Add webhook URL to config
- [ ] POST JSON payload on each alert
- [ ] Include: alert type, data, timestamp
- [ ] Retry logic for failed deliveries

### News Integration
- [ ] Research news APIs (Adjacent News, etc.)
- [ ] Create `polyterm/api/news.py`
- [ ] `polyterm news` command
- [ ] `polyterm news --market X`
- [ ] News sentiment in predictions

### Position Simulator
- [ ] `polyterm simulate` command
- [ ] Input: market, position (YES/NO), amount
- [ ] Output:
  - [ ] Entry price
  - [ ] Breakeven
  - [ ] Max profit
  - [ ] Max loss
  - [ ] P&L at different prices

---

## UX Polish (Ongoing)

### TUI Improvements
- [ ] Search functionality in main menu (type to filter)
- [ ] Breadcrumb navigation
- [ ] Screen history (back button)
- [ ] Customizable shortcuts in config
- [ ] Sparkline charts for price history

### Visual Improvements
- [ ] Light/dark theme toggle
- [ ] High contrast mode
- [ ] Better Unicode charts
- [ ] Responsive layouts for different terminal sizes

### Performance
- [ ] Cache API responses (5-second TTL)
- [ ] Lazy load screens
- [ ] Background refresh for live data
- [ ] Progress indicators for slow operations

---

## Testing Checklist

### New Commands
- [ ] Tutorial: test full walkthrough
- [ ] Glossary: test search, all terms displayed
- [ ] Disputes: mock UMA API responses
- [ ] Parlay: test calculation accuracy
- [ ] Simulate: test P&L calculations

### Integration Tests
- [ ] Help system shows correct content per screen
- [ ] Copy trading alerts fire correctly
- [ ] Wash detection identifies known patterns
- [ ] Risk scores calculate consistently

### UX Tests
- [ ] First-run flow works correctly
- [ ] Tutorial can be skipped
- [ ] Error messages are helpful
- [ ] ? key works on all screens

---

## Documentation Updates

- [ ] Update README with new features
- [ ] Update CLAUDE.md with new commands
- [ ] Add tutorial section to docs
- [ ] Document copy trading feature
- [ ] Document UMA dispute tracking
- [ ] Add SDK documentation (when ready)

---

## Marketing Checklist

- [ ] Write announcement post for v0.5.0
- [ ] Create demo GIF of tutorial
- [ ] Post to r/polymarket
- [ ] Post to Polymarket Discord
- [ ] Tweet thread with features
- [ ] Submit to Hacker News (terminal angle)

---

## Version Milestones

| Version | Focus | Key Deliverable |
|---------|-------|-----------------|
| v0.5.0 | Beginners | Tutorial + Help system |
| v0.6.0 | Intelligence | Dispute tracker + Wash detection |
| v0.7.0 | Social | Copy trading + Leaderboard |
| v0.8.0 | Professional | SDK + Webhooks |
| v1.0.0 | Polish | Full documentation + Stability |
