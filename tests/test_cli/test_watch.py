"""CLI tests for watch outage and degraded reporting. No live network."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli
from polyterm.core.service_health import SourceProbe, combine_health
from polyterm.api.status import unknown_status_snapshot


def _config_mock():
    mock_config = Mock()
    mock_config.gamma_base_url = "https://gamma.example.com"
    mock_config.gamma_api_key = ""
    mock_config.clob_rest_endpoint = "https://clob.example.com"
    mock_config.clob_endpoint = "wss://clob.example.com/ws"
    return mock_config


def _client_mocks():
    gamma = Mock()
    clob = Mock()
    status_client = Mock()
    status_client.get_summary.return_value = unknown_status_snapshot(
        reachable=False, error="mocked status page"
    )
    return gamma, clob, status_client


@patch("polyterm.cli.commands.watch.AlertEngine")
@patch("polyterm.cli.commands.watch.StatusPageClient")
@patch("polyterm.cli.commands.watch.CLOBClient")
@patch("polyterm.cli.commands.watch.GammaClient")
@patch("polyterm.cli.main.Config")
def test_watch_json_both_apis_fail_is_outage(
    mock_config_cls,
    mock_gamma_cls,
    mock_clob_cls,
    mock_status_cls,
    mock_engine_cls,
):
    mock_config_cls.return_value = _config_mock()
    gamma, clob, status_client = _client_mocks()
    gamma.get_markets.side_effect = Exception("Gamma down")
    clob.get_current_markets.side_effect = Exception("CLOB down")
    mock_gamma_cls.return_value = gamma
    mock_clob_cls.return_value = clob
    mock_status_cls.return_value = status_client

    result = CliRunner().invoke(
        cli, ["watch", "--market", "bitcoin", "--format", "json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["mode"] == "outage"
    assert payload["status"] == "outage"
    assert payload["results"]
    assert payload["results"][0]["mode"] == "outage"
    mock_engine_cls.return_value.run_once.assert_not_called()
    gamma.close.assert_called_once()
    clob.close.assert_called_once()


@patch("polyterm.cli.commands.watch.AlertEngine")
@patch("polyterm.cli.commands.watch.StatusPageClient")
@patch("polyterm.cli.commands.watch.CLOBClient")
@patch("polyterm.cli.commands.watch.GammaClient")
@patch("polyterm.cli.main.Config")
def test_watch_json_gamma_down_clob_up_is_degraded(
    mock_config_cls,
    mock_gamma_cls,
    mock_clob_cls,
    mock_status_cls,
    mock_engine_cls,
):
    mock_config_cls.return_value = _config_mock()
    gamma, clob, status_client = _client_mocks()
    gamma.get_markets.side_effect = Exception("Gamma timeout")
    clob.get_current_markets.return_value = [{"id": "c1"}]
    mock_gamma_cls.return_value = gamma
    mock_clob_cls.return_value = clob
    mock_status_cls.return_value = status_client

    result = CliRunner().invoke(
        cli, ["watch", "--market", "bitcoin", "--format", "json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["status"] == "degraded"
    assert payload["mode"] == "degraded"
    mock_engine_cls.return_value.run_once.assert_not_called()


@patch("polyterm.cli.commands.watch.AlertEngine")
@patch("polyterm.cli.commands.watch.StatusPageClient")
@patch("polyterm.cli.commands.watch.CLOBClient")
@patch("polyterm.cli.commands.watch.GammaClient")
@patch("polyterm.cli.main.Config")
def test_watch_json_clob_down_still_scans_as_degraded(
    mock_config_cls,
    mock_gamma_cls,
    mock_clob_cls,
    mock_status_cls,
    mock_engine_cls,
):
    mock_config_cls.return_value = _config_mock()
    gamma, clob, status_client = _client_mocks()
    gamma.get_markets.return_value = [{"id": "m1"}]
    clob.get_current_markets.side_effect = Exception("CLOB timeout")
    mock_gamma_cls.return_value = gamma
    mock_clob_cls.return_value = clob
    mock_status_cls.return_value = status_client
    mock_engine_cls.return_value.run_once.return_value = {
        "market": "bitcoin",
        "price": 0.55,
        "triggered": False,
        "reasons": [],
    }

    result = CliRunner().invoke(
        cli, ["watch", "--market", "bitcoin", "--format", "json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["status"] == "degraded"
    assert payload["mode"] == "degraded"
    assert payload["results"][0]["price"] == 0.55
    mock_engine_cls.return_value.run_once.assert_called_once()


@patch("polyterm.cli.commands.watch.AlertEngine")
@patch("polyterm.cli.commands.watch.StatusPageClient")
@patch("polyterm.cli.commands.watch.CLOBClient")
@patch("polyterm.cli.commands.watch.GammaClient")
@patch("polyterm.cli.main.Config")
def test_watch_json_status_page_down_is_not_operational(
    mock_config_cls,
    mock_gamma_cls,
    mock_clob_cls,
    mock_status_cls,
    mock_engine_cls,
):
    mock_config_cls.return_value = _config_mock()
    gamma, clob, status_client = _client_mocks()
    gamma.get_markets.return_value = [{"id": "m1"}]
    clob.get_current_markets.return_value = [{"id": "c1"}]
    mock_gamma_cls.return_value = gamma
    mock_clob_cls.return_value = clob
    mock_status_cls.return_value = status_client
    mock_engine_cls.return_value.run_once.return_value = {
        "market": "bitcoin",
        "price": 0.40,
        "triggered": False,
        "reasons": [],
    }

    result = CliRunner().invoke(
        cli, ["watch", "--market", "bitcoin", "--format", "json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["mode"] == "status_unknown"
    assert payload["mode"] != "operational"
    assert payload["health"]["status_page"]["indicator"] == "status_unknown"


@patch("polyterm.cli.commands.watch.StatusPageClient")
@patch("polyterm.cli.commands.watch.CLOBClient")
@patch("polyterm.cli.commands.watch.GammaClient")
@patch("polyterm.cli.main.Config")
def test_watch_table_outage_is_not_no_markets_found(
    mock_config_cls,
    mock_gamma_cls,
    mock_clob_cls,
    mock_status_cls,
):
    mock_config_cls.return_value = _config_mock()
    gamma, clob, status_client = _client_mocks()
    gamma.get_markets.side_effect = Exception("Gamma down")
    clob.get_current_markets.side_effect = Exception("CLOB down")
    mock_gamma_cls.return_value = gamma
    mock_clob_cls.return_value = clob
    mock_status_cls.return_value = status_client

    result = CliRunner().invoke(cli, ["watch", "--market", "bitcoin"])

    assert result.exit_code == 0, result.output
    assert "outage" in result.output.lower()
    assert "no markets found" not in result.output.lower()
    gamma.search_markets.assert_not_called()


def test_watch_help_mentions_outage_honesty():
    result = CliRunner().invoke(cli, ["watch", "--help"])
    assert result.exit_code == 0, result.output
    assert "watch" in result.output.lower()
    assert "--market" in result.output
    assert "outage" in result.output.lower() or "status_unknown" in result.output.lower()


def test_combine_health_outage_payload_shape():
    health = combine_health(
        SourceProbe("gamma", ok=False, error="down"),
        SourceProbe("clob", ok=False, error="down"),
        unknown_status_snapshot(reachable=False, error="offline"),
    )
    payload = health.to_dict()
    assert payload["mode"] == "outage"
    assert payload["status"] == "outage"
    assert payload["gamma"]["ok"] is False
    assert payload["clob"]["ok"] is False
