"""Watch-session wallet position. Stubbed Data API, no network."""

from unittest.mock import Mock

import pytest

from polyterm.api.data_api_lag import QUALITY_FLAG
from polyterm.core.watch_loop import collect_watch_surfaces
from polyterm.core.watch_position import (
    configured_wallet_address,
    fetch_watch_position,
    matching_market_rows,
    watch_position_dashboard_line,
)
from polyterm.core.print_scanner import PrintScanner


WALLET = "0x0000000000000000000000000000000000000001"
CONDITION = "0xcond"


class _FakeWalletAPI:
    def __init__(self, positions=None, activity=None, positions_error=None, activity_error=None):
        self.positions = positions if positions is not None else []
        self.activity = activity if activity is not None else []
        self.positions_error = positions_error
        self.activity_error = activity_error
        self.position_calls = []
        self.activity_calls = []

    def get_positions(self, address, limit=100, offset=0, sort_by="CURRENT", size_threshold=None, market=None):
        self.position_calls.append({
            "address": address,
            "limit": limit,
            "offset": offset,
            "size_threshold": size_threshold,
            "market": market,
        })
        if self.positions_error:
            raise self.positions_error
        if offset == 0:
            return self.positions
        return []

    def get_activity(self, address, limit=100, offset=0, activity_type=None, sort_direction=None, market=None):
        self.activity_calls.append({
            "address": address,
            "limit": limit,
            "offset": offset,
            "sort_direction": sort_direction,
            "market": market,
        })
        if self.activity_error:
            raise self.activity_error
        if offset == 0:
            return self.activity
        return []

    def get_trades(self, **kwargs):
        return []

    def get_recent_trades(self, **kwargs):
        return []


def _market():
    return {
        "id": "99",
        "conditionId": CONDITION,
        "slug": "bitcoin-100k",
        "clobTokenIds": ["tok-yes"],
        "question": "Bitcoin 100k?",
    }


def test_configured_wallet_address_omits_missing_and_non_strings():
    assert configured_wallet_address(None) is None
    assert configured_wallet_address(Mock()) is None
    empty = Mock()
    empty.wallet_address = ""
    empty.get.return_value = ""
    assert configured_wallet_address(empty) is None
    cfg = Mock()
    cfg.wallet_address = f"  {WALLET}  "
    cfg.get.return_value = Mock()
    assert configured_wallet_address(cfg) == WALLET


def test_configured_wallet_address_reads_get_side_effect_not_mock_attr():
    """CLI tests bind wallet via Config.get('wallet.address'); Mock arity varies."""
    cfg = Mock()
    cfg.wallet_address = ""

    def _get(key, default=""):
        if key == "wallet.address":
            return WALLET
        return default

    cfg.get.side_effect = _get
    assert configured_wallet_address(cfg) == WALLET


def test_configured_wallet_address_one_arg_get():
    cfg = Mock()
    cfg.wallet_address = ""

    def _get(key):
        if key == "wallet.address":
            return f"  {WALLET}  "
        raise KeyError(key)

    cfg.get.side_effect = _get
    assert configured_wallet_address(cfg) == WALLET


def test_configured_wallet_address_rejects_non_string_get_without_wallet_attr():
    cfg = Mock()
    cfg.wallet_address = Mock()
    cfg.get.return_value = Mock()
    assert configured_wallet_address(cfg) is None


def test_fetch_watch_position_no_wallet_is_omitted():
    api = _FakeWalletAPI(positions=[{"conditionId": CONDITION, "size": 10, "outcome": "Yes"}])
    assert fetch_watch_position(api, None, _market(), "bitcoin") is None
    assert fetch_watch_position(api, "", _market(), "bitcoin") is None
    assert fetch_watch_position(api, "   ", _market(), "bitcoin") is None
    assert api.position_calls == []


def test_fetch_watch_position_with_shares_is_lagged_not_cashpnl():
    api = _FakeWalletAPI(
        positions=[{
            "conditionId": CONDITION,
            "size": 120,
            "outcome": "Yes",
            "currentValue": 40,
            "cashPnl": -999,
            "pnl": -999,
        }],
        activity=[
            {"type": "BUY", "usdcSize": 100, "conditionId": CONDITION, "cashPnl": -50},
            {"type": "SELL", "usdcSize": 30, "conditionId": CONDITION},
        ],
    )
    payload = fetch_watch_position(api, WALLET, _market(), "bitcoin")
    assert payload is not None
    assert payload["wallet"] == WALLET
    assert payload["has_position"] is True
    assert payload["shares"] == 120.0
    assert payload["outcome"] == "Yes"
    assert payload["source"] == "data_api"
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]
    assert "cashPnl" not in payload
    assert payload["pnl"] != -999
    assert payload["cashflow"] == -70.0
    assert payload["open_mark"] == 40.0
    assert payload["pnl"] == pytest.approx(-30.0)
    assert payload["pnl_source"] == "activity-cashflow"
    assert api.position_calls[0]["market"] == CONDITION
    assert api.position_calls[0]["size_threshold"] == 0
    assert api.activity_calls[0]["sort_direction"] == "ASC"
    assert api.activity_calls[0]["market"] == CONDITION


def test_fetch_watch_position_empty_is_no_position_not_zero_book():
    api = _FakeWalletAPI(positions=[], activity=[])
    payload = fetch_watch_position(api, WALLET, _market(), "bitcoin")
    assert payload["has_position"] is False
    assert "shares" not in payload
    assert "outcome" not in payload
    assert "pnl" not in payload
    assert "cashflow" not in payload
    assert payload.get("shares") != 0
    assert payload.get("pnl") != 0
    assert "empty_position" in payload["quality_flags"]
    assert payload["lagged"] is True
    assert payload["source"] == "data_api"


def test_fetch_watch_position_filters_other_markets():
    api = _FakeWalletAPI(
        positions=[
            {"conditionId": "0xother", "size": 999, "outcome": "Yes", "currentValue": 1},
            {"conditionId": CONDITION, "size": 5, "outcome": "No", "currentValue": 2},
        ],
        activity=[
            {"type": "BUY", "usdcSize": 8, "conditionId": "0xother"},
            {"type": "BUY", "usdcSize": 3, "conditionId": CONDITION},
        ],
    )
    payload = fetch_watch_position(api, WALLET, _market(), "bitcoin")
    assert payload["shares"] == 5.0
    assert payload["outcome"] == "No"
    assert payload["cashflow"] == -3.0


def test_fetch_watch_position_network_failure_does_not_raise():
    api = _FakeWalletAPI(positions_error=RuntimeError("data api down"))
    payload = fetch_watch_position(api, WALLET, _market(), "bitcoin")
    assert payload["wallet"] == WALLET
    assert payload["has_position"] is False
    assert "shares" not in payload
    assert "position_unavailable" in payload["quality_flags"]
    assert payload.get("position_error")
    assert payload["lagged"] is True
    assert QUALITY_FLAG in payload["quality_flags"]


def test_fetch_watch_position_activity_failure_keeps_shares():
    api = _FakeWalletAPI(
        positions=[{"conditionId": CONDITION, "size": 8, "outcome": "Yes", "currentValue": 4}],
        activity_error=RuntimeError("activity down"),
    )
    payload = fetch_watch_position(api, WALLET, _market(), "bitcoin")
    assert payload["has_position"] is True
    assert payload["shares"] == 8.0
    assert "pnl" not in payload
    assert "cashflow_unavailable" in payload["quality_flags"]


def test_dashboard_line_omits_without_wallet_and_labels_empty():
    assert watch_position_dashboard_line(None) == ""
    assert watch_position_dashboard_line({}) == ""
    empty = fetch_watch_position(_FakeWalletAPI(), WALLET, _market(), "bitcoin")
    line = watch_position_dashboard_line(empty)
    assert "Wallet:" in line
    assert "no position" in line
    assert "lagged Data API" in line
    assert "0 Yes" not in line
    assert "$0.00" not in line


def test_dashboard_line_shows_shares_outcome_and_cashflow_pnl():
    payload = fetch_watch_position(
        _FakeWalletAPI(
            positions=[{"conditionId": CONDITION, "size": 120, "outcome": "Yes", "currentValue": 40}],
            activity=[{"type": "BUY", "usdcSize": 100, "conditionId": CONDITION}],
        ),
        WALLET,
        _market(),
        "bitcoin",
    )
    line = watch_position_dashboard_line(payload)
    assert "120 Yes" in line
    assert "cashflow P&L" in line
    assert "lagged Data API" in line
    assert "0x0000…0001" in line


def test_matching_market_rows_does_not_invent_a_hit():
    rows = matching_market_rows(
        [{"conditionId": "0xother", "size": 1}],
        [CONDITION],
    )
    assert rows == []


def test_collect_watch_surfaces_omits_position_without_wallet():
    clob = Mock()
    clob.get_order_book.return_value = {"bids": [], "asks": []}
    surfaces = collect_watch_surfaces(
        market="bitcoin",
        gamma_client=None,
        clob_client=clob,
        print_scanner=PrintScanner(data_api=_FakeWalletAPI()),
        market_data=_market(),
    )
    assert "position" not in surfaces


def test_collect_watch_surfaces_includes_lagged_position():
    clob = Mock()
    clob.get_order_book.return_value = {"bids": [], "asks": []}
    api = _FakeWalletAPI(
        positions=[{"conditionId": CONDITION, "size": 3, "outcome": "Yes", "currentValue": 1}],
        activity=[],
    )
    surfaces = collect_watch_surfaces(
        market="bitcoin",
        gamma_client=None,
        clob_client=clob,
        print_scanner=PrintScanner(data_api=api),
        market_data=_market(),
        wallet_address=WALLET,
    )
    position = surfaces["position"]
    assert position["has_position"] is True
    assert position["shares"] == 3.0
    assert position["lagged"] is True
    assert position["source"] == "data_api"


def test_collect_watch_surfaces_position_error_does_not_drop_book():
    clob = Mock()
    clob.get_order_book.return_value = {
        "bids": [{"price": "0.44", "size": "10"}],
        "asks": [{"price": "0.45", "size": "12"}],
    }
    api = _FakeWalletAPI(positions_error=RuntimeError("timeout"))
    surfaces = collect_watch_surfaces(
        market="bitcoin",
        gamma_client=None,
        clob_client=clob,
        print_scanner=PrintScanner(data_api=api),
        market_data=_market(),
        wallet_address=WALLET,
    )
    assert surfaces["book"]["best_bid"] == 0.44
    assert surfaces["position"]["has_position"] is False
    assert "position_unavailable" in surfaces["position"]["quality_flags"]
