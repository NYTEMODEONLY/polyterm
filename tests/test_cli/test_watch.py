"""CLI tests for watch outage, prints, and frozen-WS labels. No live network."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.api.data_api_lag import QUALITY_FLAG
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


def _empty_prints():
    return {
        "source": "data_api",
        "lag": True,
        "lagged": True,
        "prints": [],
        "count": 0,
        "fetched": 0,
        "skipped": 0,
        "quality_flags": [QUALITY_FLAG, "empty_data_api_page"],
    }


def _stub_print_scanner(mock_scanner_cls, payload=None):
    inst = Mock()
    inst.fetch_prints.return_value = payload if payload is not None else _empty_prints()
    mock_scanner_cls.return_value = inst
    return inst


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


@patch("polyterm.cli.commands.watch.PrintScanner")
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
    mock_scanner_cls,
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
    _stub_print_scanner(mock_scanner_cls)

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


@patch("polyterm.cli.commands.watch.PrintScanner")
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
    mock_scanner_cls,
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
    _stub_print_scanner(mock_scanner_cls)

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


def test_watch_help_mentions_frozen_ws_and_prints():
    result = CliRunner().invoke(cli, ["watch", "--help"])
    assert result.exit_code == 0, result.output
    output = result.output.lower()
    assert "--min-notional" in result.output
    assert "--stale-after" in result.output
    assert "print" in output
    assert "stale" in output or "book tick" in output or "ws" in output
    assert "lagged" in output or "data api" in output


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


@patch("polyterm.cli.commands.watch.PrintScanner")
@patch("polyterm.cli.commands.watch.AlertEngine")
@patch("polyterm.cli.commands.watch.StatusPageClient")
@patch("polyterm.cli.commands.watch.CLOBClient")
@patch("polyterm.cli.commands.watch.GammaClient")
@patch("polyterm.cli.main.Config")
def test_watch_json_includes_prints_lag_and_book_source(
    mock_config_cls,
    mock_gamma_cls,
    mock_clob_cls,
    mock_status_cls,
    mock_engine_cls,
    mock_scanner_cls,
):
    mock_config_cls.return_value = _config_mock()
    gamma, clob, status_client = _client_mocks()
    gamma.get_markets.return_value = [{"id": "m1"}]
    gamma.get_market.return_value = {
        "id": "m1",
        "conditionId": "0xcond",
        "slug": "bitcoin-100k",
        "clobTokenIds": ["tok-yes"],
        "question": "Bitcoin 100k?",
    }
    clob.get_current_markets.return_value = [{"id": "c1"}]
    clob.get_order_book.return_value = {
        "bids": [{"price": "0.55", "size": "10"}],
        "asks": [{"price": "0.56", "size": "9"}],
    }
    mock_gamma_cls.return_value = gamma
    mock_clob_cls.return_value = clob
    mock_status_cls.return_value = status_client
    mock_engine_cls.return_value.run_once.return_value = {
        "market": "bitcoin",
        "price": 0.55,
        "triggered": False,
        "reasons": [],
    }
    _stub_print_scanner(mock_scanner_cls, {
        "source": "data_api",
        "lag": True,
        "lagged": True,
        "prints": [{
            "wallet": "0xabc",
            "side": "BUY",
            "notional": 12000,
            "transaction_hash": "0xtx",
            "source": "data_api",
            "lag": True,
            "lagged": True,
        }],
        "count": 1,
        "fetched": 1,
        "skipped": 0,
        "quality_flags": [QUALITY_FLAG],
    })

    result = CliRunner().invoke(
        cli, ["watch", "--market", "bitcoin", "--format", "json", "--runs", "1"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"]
    assert payload["status"]
    scan = payload["results"][0]
    prints = scan["prints"]
    assert prints["lag"] is True
    assert prints["lagged"] is True
    assert prints["source"] == "data_api"
    assert QUALITY_FLAG in prints["quality_flags"]
    assert "live_data_api_trades" not in prints["quality_flags"]
    assert prints["prints"][0]["notional"] == 12000
    book = scan["book"]
    assert book["source"] == "clob_rest"
    assert book["live"] is False
    assert "ws_stale" in book
    stripped = result.output.lstrip()
    assert stripped.startswith("{") or stripped.startswith("[")


@patch("polyterm.cli.commands.watch.watch_notifier")
@patch("polyterm.cli.commands.watch.PrintScanner")
@patch("polyterm.cli.commands.watch.AlertEngine")
@patch("polyterm.cli.commands.watch.StatusPageClient")
@patch("polyterm.cli.commands.watch.CLOBClient")
@patch("polyterm.cli.commands.watch.GammaClient")
@patch("polyterm.cli.main.Config")
def test_watch_json_notify_not_sent_on_empty_poll(
    mock_config_cls,
    mock_gamma_cls,
    mock_clob_cls,
    mock_status_cls,
    mock_engine_cls,
    mock_scanner_cls,
    mock_watch_notifier,
):
    mock_config_cls.return_value = _config_mock()
    gamma, clob, status_client = _client_mocks()
    gamma.get_markets.return_value = [{"id": "m1"}]
    gamma.get_market.return_value = {"id": "m1", "conditionId": "0xcond"}
    clob.get_current_markets.return_value = [{"id": "c1"}]
    clob.get_order_book.return_value = {"bids": [], "asks": []}
    mock_gamma_cls.return_value = gamma
    mock_clob_cls.return_value = clob
    mock_status_cls.return_value = status_client
    mock_engine_cls.return_value.run_once.return_value = {
        "market": "bitcoin",
        "price": 0.40,
        "triggered": False,
        "reasons": [],
    }
    _stub_print_scanner(mock_scanner_cls)
    manager = Mock()
    mock_watch_notifier.return_value = manager

    result = CliRunner().invoke(
        cli,
        ["watch", "--market", "bitcoin", "--format", "json", "--notify", "telegram"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["results"][0]["notify_sent"] == []
    manager.send.assert_not_called()


@patch("polyterm.cli.commands.watch.watch_notifier")
@patch("polyterm.cli.commands.watch.PrintScanner")
@patch("polyterm.cli.commands.watch.AlertEngine")
@patch("polyterm.cli.commands.watch.StatusPageClient")
@patch("polyterm.cli.commands.watch.CLOBClient")
@patch("polyterm.cli.commands.watch.GammaClient")
@patch("polyterm.cli.main.Config")
def test_watch_json_notify_on_verified_print(
    mock_config_cls,
    mock_gamma_cls,
    mock_clob_cls,
    mock_status_cls,
    mock_engine_cls,
    mock_scanner_cls,
    mock_watch_notifier,
):
    mock_config_cls.return_value = _config_mock()
    gamma, clob, status_client = _client_mocks()
    gamma.get_markets.return_value = [{"id": "m1"}]
    gamma.get_market.return_value = {"id": "m1", "conditionId": "0xcond"}
    clob.get_current_markets.return_value = [{"id": "c1"}]
    clob.get_order_book.return_value = {"bids": [], "asks": []}
    mock_gamma_cls.return_value = gamma
    mock_clob_cls.return_value = clob
    mock_status_cls.return_value = status_client
    mock_engine_cls.return_value.run_once.return_value = {
        "market": "bitcoin",
        "price": 0.40,
        "triggered": False,
        "reasons": [],
    }
    _stub_print_scanner(mock_scanner_cls, {
        "source": "data_api",
        "lag": True,
        "lagged": True,
        "prints": [{
            "wallet": "0xabc",
            "side": "BUY",
            "notional": 25000,
            "transaction_hash": "0xtxbig",
            "source": "data_api",
            "lag": True,
            "lagged": True,
        }],
        "count": 1,
        "fetched": 1,
        "skipped": 0,
        "quality_flags": [QUALITY_FLAG],
    })
    manager = Mock()
    manager.send.return_value = {"telegram": True}
    mock_watch_notifier.return_value = manager

    result = CliRunner().invoke(
        cli,
        [
            "watch",
            "--market", "bitcoin",
            "--format", "json",
            "--notify", "telegram",
            "--min-notional", "10000",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    sent = payload["results"][0]["notify_sent"]
    assert sent
    assert sent[0]["kind"] == "print"
    assert sent[0]["sent"] is True
    manager.send.assert_called_once()
    assert "Lagged Data API print" in manager.send.call_args.kwargs["title"]
