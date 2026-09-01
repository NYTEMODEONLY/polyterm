"""Tests for activity-cashflow wallet P&L. No live network."""

import requests

from polyterm.api.data_api_lag import QUALITY_FLAG
from polyterm.core.pnl_cashflow import (
    SOURCE,
    VS_LEADERBOARD,
    CashflowPnl,
    activity_cash_delta,
    build_report,
    classify_activity_type,
    mark_open_positions,
    parse_leaderboard_profit,
    replay_cashflow,
)


LEO_ACTIVITY = [
    {"type": "BUY", "usdcSize": 1000, "cashPnl": -50, "makerPnl": 999},
    {"type": "SELL", "usdcSize": 400},
    {"type": "REDEEM", "usdcSize": 12000},
]

LEO_POSITIONS = [
    {
        "size": 10,
        "currentValue": 200,
        "cashPnl": -3500,
        "pnl": -3500,
        "makerPnl": 88,
    },
]


def _http_ok(payload):
    class _Http:
        def get(self, *args, **kwargs):
            mock = type("Resp", (), {})()
            mock.raise_for_status = lambda: None
            mock.json = lambda: payload
            return mock

    return _Http()


def test_classify_trade_side_and_direct_types():
    assert classify_activity_type({"type": "TRADE", "side": "BUY"}) == "buy"
    assert classify_activity_type({"type": "TRADE", "side": "SELL"}) == "sell"
    assert classify_activity_type({"type": "BUY"}) == "buy"
    assert classify_activity_type({"type": "REDEEM"}) == "redeem"
    assert classify_activity_type({"type": "MERGE"}) == "merge"
    assert classify_activity_type({"type": "SPLIT"}) == "split"
    assert classify_activity_type({"type": "MAKER_REBATE"}) == "rebate"
    assert classify_activity_type({"type": "TAKER_REBATE"}) == "rebate"
    assert classify_activity_type({"type": "REBATE"}) == "rebate"
    assert classify_activity_type({"type": "DEPOSIT", "usdcSize": 50}) is None
    assert classify_activity_type({"type": "FOO", "usdcSize": 10}) is None
    assert classify_activity_type("not-a-row") is None


def test_activity_cash_delta_does_not_invent_cash():
    assert activity_cash_delta({"type": "BUY", "usdcSize": 12.5}) == ("buy", -12.5)
    assert activity_cash_delta({"type": "SELL", "usdcSize": 8}) == ("sell", 8.0)
    assert activity_cash_delta({"type": "SPLIT", "usdcSize": 3}) == ("split", -3.0)
    assert activity_cash_delta({"type": "MERGE", "usdcSize": 3}) == ("merge", 3.0)
    assert activity_cash_delta({"type": "BUY"}) is None
    assert activity_cash_delta({"type": "BUY", "usdcSize": "nope"}) is None
    assert activity_cash_delta({"type": "BUY", "size": 10, "price": 0.4}) is None


def test_replay_cashflow_success_ignores_cashpnl_and_makerpnl():
    result = replay_cashflow(LEO_ACTIVITY)
    assert result["cashflow"] == 11400.0
    assert result["totals"]["buy"] == 1000.0
    assert result["totals"]["sell"] == 400.0
    assert result["totals"]["redeem"] == 12000.0
    assert result["included"] == 3
    assert result["counts"]["redeem"] == 1
    assert "cashPnl" not in result
    assert "makerPnl" not in result


def test_replay_empty_activity_is_zero_included_not_synthetic_types():
    result = replay_cashflow([])
    assert result["activity_count"] == 0
    assert result["included"] == 0
    assert result["cashflow"] == 0.0


def test_replay_malformed_and_unknown_rows_are_skipped():
    result = replay_cashflow([
        {"type": "BUY", "usdcSize": 10},
        {"type": "BUY", "usdcSize": "bad"},
        {"type": "UNKNOWN", "usdcSize": 500},
        None,
        {"type": "DEPOSIT", "usdcSize": 1000},
        {"size": 1, "price": 0.5},
    ])
    assert result["cashflow"] == -10.0
    assert result["included"] == 1
    assert result["skipped_malformed"] >= 1
    assert result["skipped_unknown"] >= 1


def test_replay_split_merge_rebate_signs():
    result = replay_cashflow([
        {"type": "SPLIT", "usdcSize": 100},
        {"type": "MERGE", "usdcSize": 40},
        {"type": "MAKER_REBATE", "usdcSize": 2},
        {"type": "TAKER_REBATE", "usdcSize": 1},
    ])
    assert result["cashflow"] == -57.0
    assert result["totals"]["split"] == 100.0
    assert result["totals"]["merge"] == 40.0
    assert result["totals"]["rebate"] == 3.0


def test_replay_missing_redeem_does_not_invent_redeem_cash():
    result = replay_cashflow([
        {"type": "TRADE", "side": "BUY", "usdcSize": 100},
        {"type": "TRADE", "side": "SELL", "usdcSize": 40},
    ])
    assert result["totals"]["redeem"] == 0.0
    assert result["counts"]["redeem"] == 0
    assert result["cashflow"] == -60.0


def test_mark_open_positions_uses_current_value_not_cashpnl():
    marked = mark_open_positions(LEO_POSITIONS + [
        {"size": 0, "currentValue": 9, "cashPnl": -1},
        {"size": 4, "curPrice": 0.5, "cashPnl": -99},
    ])
    assert marked["open_mark"] == 200.0 + 2.0
    assert marked["open_positions"] == 2
    cashpnl_sum = -3500 + -1 + -99
    assert marked["open_mark"] != cashpnl_sum


def test_parse_leaderboard_profit_reads_amount_not_makerpnl():
    assert parse_leaderboard_profit([{"amount": 11800, "makerPnl": 1}]) == 11800.0
    assert parse_leaderboard_profit([]) is None
    assert parse_leaderboard_profit({"amount": "5.5"}) == 5.5
    assert parse_leaderboard_profit(None) is None


def test_build_report_labels_lag_and_source_without_duration():
    cashflow_result = replay_cashflow(LEO_ACTIVITY)
    mark_result = mark_open_positions(LEO_POSITIONS)
    report = build_report(
        "0xabc",
        cashflow_result,
        mark_result=mark_result,
        leaderboard_profit=12000.0,
        quality_flags=[],
        empty=False,
    )
    assert report["source"] == SOURCE
    assert report["source"] == "activity-cashflow"
    assert report["vs_leaderboard"] == VS_LEADERBOARD
    assert report["vs-leaderboard"] == "pre-fee"
    assert report["lag"] is True
    assert report["lagged"] is True
    assert QUALITY_FLAG in report["quality_flags"]
    assert "live_data_api_trades" not in report["quality_flags"]
    assert "lag_seconds" not in report
    assert "lag_ms" not in report
    assert report["pnl"] == 11600.0
    assert report["cashflow"] == 11400.0
    assert report["open_mark"] == 200.0
    cashpnl_sum = sum(float(p["cashPnl"]) for p in LEO_POSITIONS)
    assert report["pnl"] != cashpnl_sum
    assert "cashPnl" not in report


def test_build_report_empty_activity_is_honest_empty():
    report = build_report(
        "0xabc",
        replay_cashflow([]),
        mark_result=mark_open_positions([]),
        leaderboard_profit=None,
        empty=True,
    )
    assert report["empty"] is True
    assert report["pnl"] is None
    assert report["cashflow"] is None
    assert report["source"] == "activity-cashflow"
    assert report["vs_leaderboard"] == "pre-fee"
    assert "empty_activity" in report["quality_flags"]
    assert report["lagged"] is True


class _Api:
    def __init__(self, activity=None, positions=None, activity_error=None):
        self.activity = activity if activity is not None else []
        self.positions = positions if positions is not None else []
        self.activity_error = activity_error
        self.activity_calls = []

    def get_activity(self, address, limit=100, offset=0, activity_type=None, sort_direction=None):
        self.activity_calls.append({
            "address": address,
            "limit": limit,
            "offset": offset,
            "sort_direction": sort_direction,
        })
        if self.activity_error and offset == 0:
            raise self.activity_error
        if offset == 0:
            return self.activity
        return []

    def get_positions(self, address, limit=100, offset=0, sort_by="CURRENT", size_threshold=None):
        if offset == 0:
            return self.positions
        return []


def test_compute_does_not_report_sum_cashpnl():
    api = _Api(activity=LEO_ACTIVITY, positions=LEO_POSITIONS)
    report = CashflowPnl(data_api=api, http=_http_ok([{"amount": 11800}])).compute(
        "0x0000000000000000000000000000000000000001"
    )
    cashpnl_sum = -3500.0
    assert report["pnl"] == 11600.0
    assert report["pnl"] != cashpnl_sum
    assert report["cashflow"] == 11400.0
    assert report["source"] == "activity-cashflow"
    assert report["vs_leaderboard"] == "pre-fee"
    assert report["leaderboard_profit"] == 11800.0
    assert report["lag"] is True
    assert QUALITY_FLAG in report["quality_flags"]
    assert api.activity_calls[0]["sort_direction"] == "ASC"


def test_compute_empty_activity():
    api = _Api(activity=[], positions=[])
    report = CashflowPnl(data_api=api, http=_http_ok([])).compute("0xabc")
    assert report["empty"] is True
    assert report["pnl"] is None
    assert report["cashflow"] is None
    assert "empty_activity" in report["quality_flags"]
    assert report["source"] == "activity-cashflow"


def test_compute_activity_error_raises():
    api = _Api(activity_error=requests.ConnectionError("down"))
    engine = CashflowPnl(data_api=api, http=_http_ok([]))
    try:
        engine.compute("0xabc")
        raised = False
    except requests.ConnectionError:
        raised = True
    assert raised is True


def test_compute_leaderboard_error_is_null_not_fake_fees():
    http = type("Http", (), {})()
    http.get = lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("lb down"))
    api = _Api(activity=LEO_ACTIVITY, positions=LEO_POSITIONS)
    report = CashflowPnl(data_api=api, http=http).compute("0xabc")
    assert report["leaderboard_profit"] is None
    assert "leaderboard_profit_unavailable" in report["quality_flags"]
    assert report["pnl"] == 11600.0
    assert "fee" not in (report.get("quality_flags") or [])


def test_compute_missing_redeem_keeps_cashflow_without_inventing():
    api = _Api(
        activity=[{"type": "BUY", "usdcSize": 80}, {"type": "SELL", "usdcSize": 50}],
        positions=[],
    )
    report = CashflowPnl(data_api=api, http=_http_ok([{"amount": 1}])).compute("0xabc")
    assert report["included_counts"]["redeem"] == 0
    assert report["cashflow"] == -30.0
    assert report["open_mark"] == 0.0
    assert report["pnl"] == -30.0
