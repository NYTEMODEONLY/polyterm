# Lessons

- 2026-02-16: Initialized. No corrections recorded yet in this audit session.
- 2026-02-16: For every CLI command that supports `--format json`, enforce a strict contract: no banners, headings, progress text, or warnings on stdout before/after JSON payloads.
- 2026-02-16: Avoid deprecated or optional external sources (Subgraph) in hot command paths unless strictly required; prefer explicit optional dependencies with fallbacks.
- 2026-02-16: Never assume Gamma payload nesting; API clients that call `/markets` must support flat market rows and derive event-level groupings explicitly.
- 2026-02-16: Normalize parsed datetimes to a single timezone-aware standard (UTC) at parse boundaries before sorting/filtering to avoid runtime `TypeError` and timezone drift.
- 2026-02-16: Feature capability caches must be keyed to permanent failures only (e.g., 404/422), not transient transport/server errors.
- 2026-02-16: Avoid direct list indexing on optional API fields (e.g., `clobTokenIds[0]`); parse defensively and tolerate empty/malformed payloads so one bad row cannot fail a full scan.
- 2026-02-16: If a CLI accepts wallet scope, enforce it in the data query layer and back it with DB schema support/tests; never compute scope inputs and then ignore them.
