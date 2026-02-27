"""CLI regressions for chart command CLOB history behavior."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli


def _build_market_payload():
    return {
        "id": "market-1",
        "question": "Will BTC hit 100k?",
        "outcomePrices": ["0.55"],
        "clobTokenIds": ["token-1"],
    }


@patch("polyterm.cli.main.Config")
def test_chart_passes_hours_window_to_clob_history(mock_config_cls):
    """Chart should pass explicit start/end timestamps to CLOB history fetches."""
    mock_config = Mock()
    mock_config.gamma_base_url = "https://gamma.example.com"
    mock_config.gamma_api_key = "test-key"
    mock_config.clob_rest_endpoint = "https://clob.example.com"
    mock_config_cls.return_value = mock_config

    with (
        patch("polyterm.cli.commands.chart.GammaClient") as mock_gamma_cls,
        patch("polyterm.cli.commands.chart.Database") as mock_db_cls,
        patch("polyterm.cli.commands.chart.CLOBClient") as mock_clob_cls,
    ):
        mock_gamma = Mock()
        mock_gamma.search_markets.return_value = [_build_market_payload()]
        mock_gamma_cls.return_value = mock_gamma

        now = datetime.now()
        mock_db = Mock()
        mock_db.get_market_history.return_value = [
            SimpleNamespace(timestamp=now - timedelta(hours=1), probability=0.54),
            SimpleNamespace(timestamp=now, probability=0.56),
        ]
        mock_db_cls.return_value = mock_db

        mock_clob = Mock()
        mock_clob.get_price_history.return_value = []
        mock_clob_cls.return_value = mock_clob

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chart", "--market", "bitcoin", "--hours", "72", "--format", "json"],
        )

        assert result.exit_code == 0
        kwargs = mock_clob.get_price_history.call_args.kwargs
        assert kwargs["interval"] == "max"
        assert kwargs["fidelity"] == 3600
        assert kwargs["end_ts"] - kwargs["start_ts"] == 72 * 3600
        mock_clob.close.assert_called_once()


@patch("polyterm.cli.main.Config")
def test_chart_closes_clob_client_when_history_fetch_raises(mock_config_cls):
    """Chart should always close temporary CLOB client even on API errors."""
    mock_config = Mock()
    mock_config.gamma_base_url = "https://gamma.example.com"
    mock_config.gamma_api_key = "test-key"
    mock_config.clob_rest_endpoint = "https://clob.example.com"
    mock_config_cls.return_value = mock_config

    with (
        patch("polyterm.cli.commands.chart.GammaClient") as mock_gamma_cls,
        patch("polyterm.cli.commands.chart.Database") as mock_db_cls,
        patch("polyterm.cli.commands.chart.CLOBClient") as mock_clob_cls,
    ):
        mock_gamma = Mock()
        mock_gamma.search_markets.return_value = [_build_market_payload()]
        mock_gamma_cls.return_value = mock_gamma

        now = datetime.now()
        mock_db = Mock()
        mock_db.get_market_history.return_value = [
            SimpleNamespace(timestamp=now - timedelta(hours=2), probability=0.53),
            SimpleNamespace(timestamp=now, probability=0.55),
        ]
        mock_db_cls.return_value = mock_db

        mock_clob = Mock()
        mock_clob.get_price_history.side_effect = Exception("history failed")
        mock_clob_cls.return_value = mock_clob

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chart", "--market", "bitcoin", "--hours", "6", "--format", "json"],
        )

        assert result.exit_code == 0
        mock_clob.get_price_history.assert_called_once()
        mock_clob.close.assert_called_once()
