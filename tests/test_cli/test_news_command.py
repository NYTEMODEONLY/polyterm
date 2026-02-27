"""CLI tests for news command behavior."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli


@patch("polyterm.cli.commands.news.NewsAggregator")
@patch("polyterm.cli.main.Config")
def test_news_market_mode_passes_hours_to_aggregator(mock_config_cls, mock_aggregator_cls):
    """`news --market` should apply the same --hours filter as global mode."""
    mock_config = Mock()
    mock_config_cls.return_value = mock_config

    mock_aggregator = Mock()
    mock_aggregator.get_market_news.return_value = []
    mock_aggregator_cls.return_value = mock_aggregator

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["news", "--market", "bitcoin", "--hours", "1", "--limit", "5", "--format", "json"],
    )

    assert result.exit_code == 0
    mock_aggregator.get_market_news.assert_called_once_with("bitcoin", limit=5, hours=1)
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["market"] == "bitcoin"
    assert payload["hours"] == 1
