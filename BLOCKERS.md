# CI Foundation - Blockers

## Workflow Push Blocked by OAuth Token Scope

**Status**: The GitHub Actions workflow file (`.github/workflows/ci.yml`) is ready but cannot be pushed because the OAuth token (`gho_*`) lacks the `workflow` scope.

**Error**:
```
! [remote rejected] swarm/polyterm-ci-foundation -> swarm/polyterm-ci-foundation
(refusing to allow an OAuth App to create or update workflow `.github/workflows/ci.yml` without `workflow` scope)
```

**Resolution options** (pick one):
1. Run `gh auth refresh -h github.com -s workflow` interactively to add the `workflow` scope, then `git push`.
2. Use a Personal Access Token (PAT) with `repo` + `workflow` scopes.
3. Manually create `.github/workflows/ci.yml` via the GitHub web UI (file contents are in the PR description).

**What's ready**:
- `.github/workflows/ci.yml` exists locally and is validated
- `CONTRIBUTING.md` updated with CI checks documentation (already pushed)
- All 410 tests pass locally in 17.62s
- All 232 Python files pass syntax check
- All 5 import smoke tests pass

**Files to push once unblocked**:
- `.github/workflows/ci.yml` (new file, 81 lines)
