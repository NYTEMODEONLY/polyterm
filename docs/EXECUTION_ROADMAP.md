# Execution Roadmap

**Last updated:** 2026-02-25
**Context:** Response to Polymarket official CLI launch (Feb 24, 2026)
**Team model:** 1 engineer + swarm agents

---

## Priority Tiers

### P0: Defend Core Value (Week 1-2) — Ship or lose users

These items close gaps that could cause users to switch to the official CLI for basic market browsing, or fail to capitalize on our unique advantages.

| # | Initiative | Owner Role | Effort | Success Metric | Acceptance Criteria |
|---|-----------|------------|--------|----------------|---------------------|
| P0-1 | **Add CLOB price-history API** | Backend | M | Price history available without local snapshots | `polyterm chart -m <slug>` shows data on first run (no cold start). Supports 1m, 1h, 6h, 1d, 1w intervals. Falls back to local snapshots if API fails. |
| P0-2 | **Unified "Trade Thesis" view** | Full-stack | L | Single command shows signals + risk + whale + wash trade status | `polyterm analyze -m <slug>` returns prediction signal, risk grade (A-F), whale alignment (for/against), wash trade risk level, UMA dispute risk, and arbitrage opportunity (if any). All in one screen. |
| P0-3 | **Startup time optimization** | Backend | S | CLI startup < 150ms (from ~300ms) | Lazy-import all heavy modules (Rich, requests, sqlite3). Measure with `time polyterm --version`. Benchmark before/after in CI. |
| P0-4 | **"Why PolyTerm" README section** | Docs | S | README clearly differentiates from official CLI | 8-12 line section with measurable claims. No hype. Links to COMPETITIVE_GAP.md for details. |
| P0-5 | **Fix stale Subgraph references** | Backend | S | No deprecation warnings in normal usage | Audit all Subgraph calls. Replace with Gamma/CLOB equivalents or remove. Zero deprecation warnings printed to user. |

### P1: Widen the Moat (Week 2-4) — Build what they can't easily copy

These items deepen PolyTerm's analytics advantage and make the local database more valuable over time.

| # | Initiative | Owner Role | Effort | Success Metric | Acceptance Criteria |
|---|-----------|------------|--------|----------------|---------------------|
| P1-1 | **Portfolio risk aggregation** | Backend | M | Portfolio-level risk view across all tracked positions | `polyterm risk --portfolio` shows: total exposure, correlation between positions, concentration risk, weighted risk grade. Requires >= 2 positions in DB. |
| P1-2 | **Market comments integration** | Backend | S | Users can view market comments without leaving terminal | `polyterm comments -m <slug>` shows latest 20 comments with timestamps and usernames. Uses Gamma or CLOB API. |
| P1-3 | **Leaderboard + profiles** | Backend | S | Users can look up trader performance | `polyterm leaderboard --top 25` shows top traders. `polyterm profile <address>` shows trader stats. Data from Polymarket data API. |
| P1-4 | **Scheduled analytics scans** | Backend | M | Automated periodic scans with notification output | `polyterm watch --schedule 15m --notify telegram` runs arbitrage + whale + prediction scans every N minutes and pushes results to configured notification channel. |
| P1-5 | **Cross-session trend detection** | Backend | M | Insights from accumulated local data | `polyterm trends` shows: markets with accelerating volume, new whale entries, risk grade changes, price momentum shifts. Requires >= 3 days of snapshots. |
| P1-6 | **Homebrew formula** | DevOps | S | `brew install polyterm` works | Formula published to homebrew-polyterm tap. CI auto-updates formula on release. Install tested on macOS ARM and x86. |

### P2: Strategic Expansion (Month 2-3) — New user segments

These items open PolyTerm to new audiences and use cases.

| # | Initiative | Owner Role | Effort | Success Metric | Acceptance Criteria |
|---|-----------|------------|--------|----------------|---------------------|
| P2-1 | **Multi-platform arbitrage (Kalshi, Metaculus)** | Backend | L | Cross-platform price comparison for 3+ platforms | `polyterm arbitrage --platforms polymarket,kalshi,metaculus` shows price deltas. Requires API keys for non-Polymarket platforms. Fee-adjusted profit calculation. |
| P2-2 | **Export to spreadsheet** | Backend | S | Users can export analytics to CSV/Excel | `polyterm export --format xlsx` generates spreadsheet with market data, positions, alerts, and snapshots. Works with `--format csv` too. |
| P2-3 | **Plugin/extension system** | Arch | L | Third-party analytics modules can be loaded | `polyterm plugin install <name>` loads Python modules from a registry. Plugins can add commands, screens, and data sources. Documented API with 1 example plugin. |
| P2-4 | **Web dashboard companion** | Full-stack | L | Browser-based read-only dashboard for PolyTerm data | `polyterm serve` starts local web server showing charts, positions, alerts. Uses local SQLite DB. No auth required (localhost only). |
| P2-5 | **AI agent mode** | Backend | M | PolyTerm usable as a tool by AI coding agents | `polyterm agent <query>` returns structured JSON analysis. Optimized for LLM consumption. Documented tool schema for Claude, GPT, etc. |

---

## Sprint 1 Plan (Weeks 1-2)

**Goal:** Close critical data gaps, ship the unified analysis view, and establish competitive positioning in docs.

### Day 1-2: Foundation

| Task | Items | Est. Hours |
|------|-------|------------|
| Competitive docs | P0-4 (README section) | 2h |
| Audit Subgraph usage | P0-5 (find all deprecation paths) | 3h |
| CLOB price-history research | P0-1 (API contract, test endpoint) | 2h |

**Deliverable:** README updated, Subgraph audit complete, CLOB price-history API tested manually.

### Day 3-5: Core Data

| Task | Items | Est. Hours |
|------|-------|------------|
| Implement CLOB price-history | P0-1 (API client, chart integration) | 8h |
| Remove/replace Subgraph calls | P0-5 (implement replacements) | 4h |
| Startup optimization | P0-3 (lazy imports, measurement) | 4h |

**Deliverable:** `polyterm chart` works on first run without local data. No Subgraph deprecation warnings. Startup under 150ms.

### Day 6-8: Intelligence Layer

| Task | Items | Est. Hours |
|------|-------|------------|
| Design analyze command output | P0-2 (mockup, data flow) | 2h |
| Implement analyze command | P0-2 (aggregate existing signals) | 10h |
| Add tests for analyze | P0-2 (unit + integration) | 4h |

**Deliverable:** `polyterm analyze -m <slug>` returns unified trade thesis with all signal types.

### Day 9-10: Polish & Ship

| Task | Items | Est. Hours |
|------|-------|------------|
| Integration testing | All P0 items | 4h |
| Update CLAUDE.md | Document new commands | 1h |
| Version bump + release | Tag v0.9.0 | 2h |
| Backlog grooming | P1 items scoped for Sprint 2 | 2h |

**Deliverable:** v0.9.0 released with all P0 items complete. P1 backlog ready.

### Sprint 1 Success Criteria

- [ ] `polyterm chart -m bitcoin` returns data on a fresh install (no local snapshots needed)
- [ ] `polyterm analyze -m bitcoin` returns unified trade thesis in <3 seconds
- [ ] `time polyterm --version` completes in <150ms
- [ ] Zero Subgraph deprecation warnings in normal usage
- [ ] README has "Why PolyTerm" section with measurable claims
- [ ] 440+ tests still passing (no regression)
- [ ] v0.9.0 published to PyPI

---

## Sprint 2 Preview (Weeks 3-4)

**Focus:** P1-1 (portfolio risk), P1-2 (comments), P1-3 (leaderboard), P1-6 (Homebrew)

These items widen the feature gap in areas where the official CLI will not invest (portfolio analytics, trend detection) and close parity gaps in areas where users expect basics (comments, leaderboard, Homebrew install).

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Polymarket CLI adds analytics features | Reduces PolyTerm's unique value | Ship faster. Our Python analytics ecosystem (Rich, numpy-style calculations) gives us speed-to-feature advantage over their Rust codebase. |
| CLOB price-history API changes | Breaks chart command | Use API aggregator fallback pattern. Local snapshots as secondary source. |
| Official CLI gets massive adoption | Reduces PolyTerm's addressable market | Position as complementary tool ("use both"). Cross-reference in docs. |
| Startup optimization hits diminishing returns | Can't match Rust performance | Target 150ms (acceptable), don't chase 10ms. Focus on perceived speed (TUI loading indicators). |
| Plugin system scope creep | Delays core analytics work | Defer to P2. Don't design until P0/P1 are shipped. |

---

## Metrics to Track

| Metric | Current | Sprint 1 Target | Sprint 2 Target |
|--------|---------|-----------------|-----------------|
| PyPI monthly downloads | Baseline TBD | +20% | +50% |
| GitHub stars | Current count | +50 | +150 |
| CLI commands | 84 | 85 (+analyze) | 88 (+comments, leaderboard, trends) |
| Test count | 440 | 460 | 500 |
| Startup time (ms) | ~300 | <150 | <150 |
| Cold-start chart support | No | Yes | Yes |
