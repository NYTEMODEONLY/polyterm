# TODO Backlog

Actionable items linked to [EXECUTION_ROADMAP.md](./EXECUTION_ROADMAP.md). Each item is scoped for implementation.

---

## P0: Defend Core Value

### TODO-1: Add CLOB price-history API to chart command
**Roadmap:** P0-1
**Priority:** P0
**Effort:** M (8h)
**Files:**
- `polyterm/api/clob.py` — Add `get_price_history(token_id, interval, fidelity)` method
- `polyterm/core/charts.py` — Accept CLOB price-history data format
- `polyterm/cli/commands/chart.py` — Try CLOB API first, fall back to local snapshots
- `tests/test_api/test_clob.py` — Mock price-history endpoint
- `tests/test_core/test_charts.py` — Test with CLOB data format

**Acceptance criteria:**
- `polyterm chart -m bitcoin` works on fresh install (zero local snapshots)
- Supports intervals: 1m, 1h, 6h, 1d, 1w
- Falls back to local DB snapshots if CLOB API fails
- No breaking changes to existing chart functionality

---

### TODO-2: Build unified "analyze" command (Trade Thesis view)
**Roadmap:** P0-2
**Priority:** P0
**Effort:** L (12h)
**Files:**
- `polyterm/cli/commands/analyze.py` — New command (aggregates existing modules)
- `polyterm/tui/screens/analyze.py` — TUI screen for analyze
- `polyterm/tui/controller.py` — Add `an` shortcut routing
- `polyterm/cli/main.py` — Register analyze command
- `tests/test_cli/test_analyze.py` — Unit tests

**Acceptance criteria:**
- `polyterm analyze -m <slug>` shows in a single view:
  - Prediction signal (direction, confidence, factors)
  - Risk grade (A-F with top risk factor)
  - Whale activity (aligned for/against, volume)
  - Wash trade risk level
  - UMA dispute risk
  - Arbitrage opportunity (if spread > 2.5%)
  - Kelly-optimal position size (given user's edge estimate)
- Completes in <3 seconds
- Works with `--format json`
- 10+ tests covering signal aggregation

---

### TODO-3: Optimize CLI startup time to <150ms
**Roadmap:** P0-3
**Priority:** P0
**Effort:** S (4h)
**Files:**
- `polyterm/cli/main.py` — Lazy-import click command groups
- `polyterm/__init__.py` — Defer Rich/DB imports
- `polyterm/cli/commands/*.py` — Move heavy imports inside functions

**Acceptance criteria:**
- `time polyterm --version` < 150ms (measured on reference hardware)
- `time polyterm monitor --help` < 200ms
- No import errors when commands are actually invoked
- Benchmark script added: `scripts/bench_startup.sh`

---

### TODO-4: Update README with "Why PolyTerm" section
**Roadmap:** P0-4
**Priority:** P0
**Effort:** S (2h)
**Files:**
- `README.md` — Add section after Quick Start

**Acceptance criteria:**
- 8-12 lines, measurable claims only
- Mentions: 20+ analytics features, 73+ TUI screens, zero custody risk, ASCII charts
- Links to `docs/COMPETITIVE_GAP.md`
- No hype adjectives, no removal of existing content

---

### TODO-5: Remove Subgraph deprecation warnings
**Roadmap:** P0-5
**Priority:** P0
**Effort:** S (3h)
**Files:**
- `polyterm/api/` — Audit all files for Subgraph references
- `polyterm/core/whale_tracker.py` — Check for Subgraph queries
- `polyterm/cli/commands/portfolio.py` — Replace Subgraph data source

**Acceptance criteria:**
- `grep -r "subgraph\|thegraph" polyterm/` returns zero hits in active code paths
- Portfolio/wallet features still work using Gamma/CLOB/local DB
- Deprecation warnings never shown to users
- Existing tests still pass

---

## P1: Widen the Moat

### TODO-6: Add portfolio-level risk aggregation
**Roadmap:** P1-1
**Priority:** P1
**Effort:** M (8h)
**Files:**
- `polyterm/core/risk_score.py` — Add `calculate_portfolio_risk(positions)` function
- `polyterm/cli/commands/risk.py` — Add `--portfolio` flag
- `polyterm/db/database.py` — Query to fetch all open positions
- `tests/test_core/test_risk_score.py` — Portfolio risk tests

**Acceptance criteria:**
- `polyterm risk --portfolio` shows: total exposure, position count, concentration %, weighted avg risk grade, correlation warning (if >3 positions in same category)
- Requires >= 2 tracked positions
- Works with `--format json`

---

### TODO-7: Add market comments viewer
**Roadmap:** P1-2
**Priority:** P1
**Effort:** S (4h)
**Files:**
- `polyterm/api/gamma.py` — Add `get_market_comments(slug, limit)` method
- `polyterm/cli/commands/comments.py` — New command
- `polyterm/cli/main.py` — Register command
- `tests/test_cli/test_comments.py` — Mock API tests

**Acceptance criteria:**
- `polyterm comments -m <slug>` shows latest 20 comments
- Each comment shows: username, timestamp, content (truncated to 200 chars)
- `--limit N` to control count
- `--format json` works

---

### TODO-8: Add leaderboard and profile commands
**Roadmap:** P1-3
**Priority:** P1
**Effort:** S (4h)
**Files:**
- `polyterm/api/gamma.py` or `polyterm/api/clob.py` — Add leaderboard/profile API methods
- `polyterm/cli/commands/leaderboard.py` — Update existing or create
- `polyterm/cli/commands/profile.py` — New command
- `tests/` — Mock API tests

**Acceptance criteria:**
- `polyterm leaderboard --top 25` shows top traders by profit
- `polyterm profile <address>` shows: total volume, profit, positions, win rate
- Data sourced from Polymarket data API
- `--format json` works

---

### TODO-9: Add Homebrew formula and install script
**Roadmap:** P1-6
**Priority:** P1
**Effort:** S (3h)
**Files:**
- `Formula/polyterm.rb` — Homebrew formula
- `install.sh` — curl-based installer
- `.github/workflows/release.yml` — Auto-update formula on release (if CI exists)

**Acceptance criteria:**
- `brew tap NYTEMODEONLY/polyterm && brew install polyterm` works
- `curl -sSL <raw-url>/install.sh | sh` works on macOS and Linux
- Install script verifies Python 3.8+ is available
- Tested on macOS ARM, macOS x86, Ubuntu 22.04

---

### TODO-10: Add scheduled analytics scans with notifications
**Roadmap:** P1-4
**Priority:** P1
**Effort:** M (8h)
**Files:**
- `polyterm/cli/commands/watch.py` — Add `--schedule` and `--notify` flags
- `polyterm/core/notifications.py` — Ensure notification channels work for scan results
- `polyterm/core/scanner.py` — Add scan-and-notify pipeline

**Acceptance criteria:**
- `polyterm watch --schedule 15m --notify telegram` runs scans every 15 minutes
- Scans include: arbitrage opportunities, whale alerts, significant price moves
- Results pushed to configured notification channel
- Graceful shutdown on Ctrl+C
- Runs as foreground process (no daemon)

---

### TODO-11: Add cross-session trend detection
**Roadmap:** P1-5
**Priority:** P1
**Effort:** M (8h)
**Files:**
- `polyterm/cli/commands/trends.py` — New command
- `polyterm/core/scanner.py` — Add trend analysis functions
- `polyterm/db/database.py` — Add snapshot comparison queries

**Acceptance criteria:**
- `polyterm trends` shows: markets with accelerating volume (>2x baseline), new whale entries (last 24h), risk grade changes, price momentum shifts
- Requires >= 3 days of local snapshots (shows message if insufficient data)
- `--days N` to control lookback window
- `--format json` works

---

## P2: Strategic Expansion

### TODO-12: Expand cross-platform arbitrage to Kalshi + Metaculus
**Roadmap:** P2-1
**Priority:** P2
**Effort:** L (16h)
**Files:**
- `polyterm/api/kalshi.py` — Kalshi API client (expand existing)
- `polyterm/api/metaculus.py` — New Metaculus API client
- `polyterm/core/arbitrage.py` — Multi-platform comparison logic
- `polyterm/cli/commands/arbitrage.py` — Add `--platforms` flag

**Acceptance criteria:**
- `polyterm arbitrage --platforms polymarket,kalshi` shows cross-platform price deltas
- Fee-adjusted profit calculation for each platform
- API keys configurable in `~/.polyterm/config.toml`
- Graceful degradation if a platform API is unavailable

---

### TODO-13: Add AI agent mode for LLM tool use
**Roadmap:** P2-5
**Priority:** P2
**Effort:** M (8h)
**Files:**
- `polyterm/cli/commands/agent.py` — New command
- `polyterm/cli/main.py` — Register command
- `docs/AGENT_MODE.md` — Tool schema documentation

**Acceptance criteria:**
- `polyterm agent "what are the best arbitrage opportunities right now?"` returns structured JSON
- Output schema documented for Claude/GPT tool use
- Supports queries: market lookup, arbitrage scan, risk assessment, whale activity, predictions
- Response time <5 seconds for any single query
- No interactive prompts (pure stdin/stdout)

---

### TODO-14: Add export to XLSX/CSV with analytics
**Roadmap:** P2-2
**Priority:** P2
**Effort:** S (4h)
**Files:**
- `polyterm/cli/commands/export.py` — Add `--format xlsx` and `--format csv`
- `setup.py` — Add `openpyxl` as optional dependency

**Acceptance criteria:**
- `polyterm export --format csv` exports market data, positions, alerts to CSV
- `polyterm export --format xlsx` generates formatted Excel workbook (optional dep)
- Column headers match JSON output keys
- File saved to current directory with timestamp in filename
