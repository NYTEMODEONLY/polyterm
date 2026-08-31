"""Tests for the quarantined demo strategy simulator."""

from polyterm.core.demo_strategy_sim import (
    DEMO_DISCLOSURE,
    DEMO_MODE,
    run_demo_simulation,
)


def test_demo_simulation_is_labeled_and_not_historical():
    result = run_demo_simulation(
        markets=[{"question": "Will it rain?", "tokens": [{"outcome": "YES", "price": 0.4}]}],
        strategy="momentum",
        days=30,
        capital=1000,
        position_size=0.1,
    )
    assert result["mode"] == DEMO_MODE
    assert result["uses_historical_data"] is False
    assert result["method"] == "seeded_random_simulation"
    assert "does not replay historical" in result["disclosure"]
    assert "does not replay historical" in DEMO_DISCLOSURE
    assert result["total_trades"] > 0
    assert "DEMO" not in result["trades"][0]["side"]


def test_demo_simulation_is_reproducible_for_same_strategy():
    markets = [{"question": "Market A", "tokens": []}]
    first = run_demo_simulation(markets, "contrarian", 7, 500, 0.2)
    second = run_demo_simulation(markets, "contrarian", 7, 500, 0.2)
    assert first["trades"] == second["trades"]
    assert first["final_capital"] == second["final_capital"]
