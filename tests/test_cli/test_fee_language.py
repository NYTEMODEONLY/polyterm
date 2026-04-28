"""CLI coverage for CLOB V2 fee wording and calculations."""

import pytest
from click.testing import CliRunner
from rich.console import Console

from polyterm.cli.commands.crypto15m import _display_trade_analysis
from polyterm.cli.commands.parlay import _calculate_parlay
from polyterm.cli.commands.size import _calculate_sizes
from polyterm.cli.main import cli
from polyterm.core.fees import estimate_taker_fee


def test_simulate_outputs_clob_v2_fee_language(tmp_path, monkeypatch):
    """The simulator should not present the old fixed-fee rule."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    result = CliRunner().invoke(
        cli,
        ["simulate", "--price", "0.65", "--amount", "100", "--side", "yes"],
    )

    assert result.exit_code == 0
    assert "Protocol Fee Estimate" in result.output
    assert "generic protocol estimate" in result.output
    assert "2% on winnings" not in result.output
    assert "Polymarket charges 2%" not in result.output


def test_size_uses_clob_v2_fee_curve():
    """Kelly sizing should account for the shared CLOB V2 fee curve."""
    result = _calculate_sizes(
        bankroll=1000,
        probability=0.65,
        odds=0.50,
        kelly_fraction=0.25,
    )

    assert result["fees"]["fee_estimate_per_dollar"] == pytest.approx(estimate_taker_fee(1, 0.50))
    assert result["fees"]["fee_source"] == "generic protocol estimate"
    assert result["outcomes"]["fee_estimate"] > 0


def test_parlay_uses_clob_v2_fee_curve():
    """Parlay payouts should use a protocol fee estimate, not fixed text."""
    probs = [0.65, 0.70]

    result = _calculate_parlay(probs, amount=100)

    assert result["fee_estimate"] == pytest.approx(estimate_taker_fee(100, 0.65 * 0.70))
    assert result["fee_source"] == "generic protocol estimate"
    assert result["roi_after_fees"] == pytest.approx(result["profit_after_fees"])


def test_crypto15m_trade_analysis_reports_market_fee_schedule():
    """15m market scenarios should report market-sourced fee schedules."""
    console = Console(record=True, width=120)
    market = {
        "question": "Bitcoin Up or Down - test",
        "crypto_symbol": "BTC",
        "outcomePrices": '["0.65", "0.35"]',
        "volume": 0,
        "liquidity": 0,
        "feeSchedule": {"rate": 0.05, "exponent": 1, "takerOnly": True},
    }

    _display_trade_analysis(console, market, clob_client=None)
    output = console.export_text()

    assert "Protocol fee estimates use market fee schedule" in output
