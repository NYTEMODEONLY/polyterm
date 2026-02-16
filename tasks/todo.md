# PolyTerm Audit Todo (2026-02-16)

- [x] 1. Establish audit baseline and environment details.
- [x] 2. VERIFY: Confirm clean git state and collect project/test inventory.
- [x] 3. Run full automated tests (`pytest`) for all modules.
- [x] 4. VERIFY: Capture pass/fail counts and failing test identifiers.
- [x] 5. Run coverage audit to detect untested production modules.
- [x] 6. VERIFY: Export per-file coverage and identify zero/low coverage files.
- [x] 7. Run packaging and CLI smoke checks (`pip install -e .`, `polyterm --help`, key command help paths).
- [x] 8. VERIFY: Confirm commands execute without runtime/import errors.
- [x] 9. Investigate failures and regressions to root cause with minimal reproductions.
- [x] 10. VERIFY: Re-run affected tests/commands and confirm findings are reproducible.
- [x] 11. Review architecture/test alignment for non-monolithic maintainability risks.
- [x] 12. VERIFY: Document concrete evidence and file-level references for each risk.
- [x] 13. Final report with severity-ranked findings, broken features list, and next fixes.
- [x] 14. VERIFY: Ensure report includes exact paths/lines, reproduction steps, and residual risks.

## Review Notes

- Automated tests: `623 passed`, `2 skipped`, `0 failed`.
- Coverage: `26%` total (`coverage.xml`), with many CLI/TUI/core modules at very low or zero coverage.
- CLI registration smoke: `81` command help paths validated, `0` failures.
- Import sweep: `208` modules imported, `0` import failures.
- Reproduced defects:
  - `crypto15m --once --format json` takes ~58s when no 15m matches are found due repeated fallback search cycles.
  - `whales --format json` emits non-JSON text before JSON payload (breaks parser workflows).
  - `mywallet --format json` emits non-JSON text before JSON payload in multiple flows and emits plain text for missing wallet.
  - Portfolio live wallet analytics degraded: command returns “Subgraph API endpoint has been removed”.
- Fix implementation completed on branch `codex/fix-json-portfolio-crypto15m`:
  - `whales --format json` now emits pure JSON only.
  - `mywallet --format json` now emits pure JSON for success and error paths.
  - Portfolio analytics now use Data API when Subgraph is unavailable; command no longer depends on deprecated Subgraph path.
  - `crypto15m --once --format json` discovery logic was rewritten to bounded API calls and now returns in ~1.9s in empty-market scenarios.
  - Subgraph initialization removed from monitor/whales code paths that do not require it.
- Verification after fixes:
  - Full suite: `630 passed`, `2 skipped`, `0 failed` (`./.venv/bin/pytest`).
  - New regression tests added for JSON output contracts, crypto15m bounded-call behavior, Data API portfolio path, and Gamma search-endpoint fallback behavior.
  - Runtime smoke checks: JSON outputs validated with `python -m json.tool`; no stderr deprecation noise on monitor/whales; portfolio command no longer surfaces Subgraph deprecation error for wallet lookup.

## PR #1 Review Remediation (2026-02-16)

- [x] 1. Re-validate open PR review comments and map each to source/tests.
- [x] 2. VERIFY: Capture current behavior and confirm each finding is reproducible from code inspection/tests.
- [x] 3. Fix `polyterm/core/negrisk.py` multi-outcome discovery for flat `/markets` payloads.
- [x] 4. VERIFY: Run `./.venv/bin/pytest tests/test_core/test_negrisk.py` and confirm flat payload regression passes.
- [x] 5. Fix `polyterm/core/news.py` datetime normalization to prevent naive/aware sort errors.
- [x] 6. VERIFY: Run `./.venv/bin/pytest tests/test_core/test_news.py` and confirm mixed-date sorting regression passes.
- [x] 7. Fix `polyterm/api/gamma.py` search-endpoint disable caching to only disable on permanent unsupported statuses.
- [x] 8. VERIFY: Run `./.venv/bin/pytest tests/test_api/test_gamma.py -k search_markets` and confirm transient 500 does not disable endpoint.
- [x] 9. Run full regression suite `./.venv/bin/pytest`.
- [x] 10. VERIFY: Confirm full pass counts and no new failures.
- [x] 11. Update `tasks/todo.md` review notes with concrete results and residual risks.

### PR #1 Review Remediation Results

- PR feedback revalidated from GitHub API: 3 inline findings (negrisk flat payload grouping, news mixed datetime sorting, gamma transient search fallback caching).
- `negrisk` fix validation: `./.venv/bin/pytest tests/test_core/test_negrisk.py` => `27 passed`.
- `news` fix validation: `./.venv/bin/pytest tests/test_core/test_news.py` => `24 passed`.
- `gamma` fix validation: `./.venv/bin/pytest tests/test_api/test_gamma.py -k search_markets` => `6 passed, 50 deselected`.
- Full regression validation: `./.venv/bin/pytest` => `633 passed, 2 skipped, 1 warning`.
- Residual risk: live upstream API payload contracts can still evolve; current tests now cover both nested and flat market/event shapes used by the reviewed paths.

## PR #1 Review Remediation Round 2 (2026-02-16)

- [x] 1. Re-validate new Codex review comments and map each to code paths/tests.
- [x] 2. VERIFY: Confirm both new findings are reproducible from current source behavior.
- [x] 3. Fix `polyterm/core/negrisk.py` to handle empty/malformed `clobTokenIds` without crashing scans.
- [x] 4. VERIFY: Run `./.venv/bin/pytest tests/test_core/test_negrisk.py` and confirm new token-id edge-case regression passes.
- [x] 5. Implement wallet-scoped position retrieval for rewards (`--wallet` and saved wallet config) in DB + command path.
- [x] 6. VERIFY: Run focused DB/CLI tests for wallet-scoped rewards behavior.
- [x] 7. Run full regression suite `./.venv/bin/pytest`.
- [x] 8. VERIFY: Confirm full pass counts and no regressions.
- [x] 9. Update PR comments/threads with fix details and validation evidence.

### PR #1 Round 2 Results

- New review findings revalidated from GitHub API: 2 inline findings (`negrisk` empty token list crash risk, `rewards` wallet filter ignored).
- `negrisk` fix validation: `./.venv/bin/pytest tests/test_core/test_negrisk.py` => `28 passed`.
- Wallet-scope DB validation: `./.venv/bin/pytest tests/test_db/test_positions.py` => `12 passed`.
- Wallet-scope CLI validation: `./.venv/bin/pytest tests/test_cli/test_rewards_command.py` => `3 passed`.
- Full regression validation: `./.venv/bin/pytest` => `639 passed, 2 skipped, 1 warning`.
- Residual risk: existing manually tracked positions created before wallet tagging may have empty `wallet_address` and will not appear in wallet-scoped rewards views until re-tagged or recreated.
