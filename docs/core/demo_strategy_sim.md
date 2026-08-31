# Demo Strategy Simulation

> Seeded random strategy simulation. This is not historical backtesting.

## Overview

The demo strategy simulator generates synthetic trades from a seeded RNG. Current Gamma market snapshots are used only as labels and a starting-price hint. Entry prices, exits, sides, and P&L are random. The module exists so `polyterm backtest` can keep a quarantined demo path without claiming historical replay.

Historical backtesting is not implemented. Use `polyterm chart` or `polyterm replay` for real historical market data.

## Usage

```python
from polyterm.core.demo_strategy_sim import run_demo_simulation, DEMO_DISCLOSURE

result = run_demo_simulation(
    markets=[{"question": "Example", "tokens": []}],
    strategy="momentum",
    days=30,
    capital=1000,
    position_size=0.1,
)
assert result["uses_historical_data"] is False
```

The CLI requires `--demo` before this function is called.

## Key Functions

| Function | Description |
|----------|-------------|
| `demo_seed(strategy)` | Stable MD5-based seed so results are reproducible across processes |
| `run_demo_simulation(markets, strategy, days, capital, position_size)` | Return labeled demo metrics and a synthetic trade log |

## Return Contract

Every result includes:

| Field | Value |
|-------|-------|
| `mode` | `demo_random_simulation` |
| `uses_historical_data` | `false` |
| `method` | `seeded_random_simulation` |
| `disclosure` | Human-readable warning that this is not a historical backtest |

Metrics such as Sharpe, win rate, and drawdown are properties of the random path. They are not evidence of a strategy's historical performance.

## Strategies

The strategy name only changes the random side/edge heuristic:

- `momentum`
- `mean-reversion`
- `whale-follow`
- `contrarian`
- `volume-spike`

None of these replay whale wallets, CLOB books, or historical fills.

## Data Sources

- Optional Gamma market list for labels and a YES-token price hint
- Seeded `random.Random`; no CLOB price history, no Data API trades

## Related

- CLI: [backtest](../cli/backtest.md)
- TUI: [backtest_screen](../tui/screens/backtest_screen.md)
- Chart (real history): [chart](../cli/chart.md)
- Replay (real history): [replay](../cli/replay.md)

## Documentation Maintenance

This page is part of the generated PolyTerm documentation set and should stay aligned with the source module.

When updating this feature:

- Confirm `polyterm/core/demo_strategy_sim.py` still exists.
- Keep the DEMO disclosure in CLI, TUI, JSON, and this page.
- Do not describe this module as historical backtesting.
- Run `.venv/bin/python scripts/validate_docs.py` before committing.

Validation expectations:

- Internal links should resolve inside the `docs/` tree.
- Workflows that cannot use live market history must say so.
- New modules should have a dedicated page rather than relying only on the index.
