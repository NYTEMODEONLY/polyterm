"""Tests for honest Data API leaderboard normalization."""

import pytest

from polyterm.core.leaderboard import (
    UnsupportedLeaderboardType,
    WINRATE_UNSUPPORTED_MESSAGE,
    data_api_sort_by,
    leaderboard_quality_flags,
    normalize_leaderboard_row,
    normalize_leaderboard_rows,
    sort_traders,
)


def test_normalize_maps_vol_and_pnl_without_fake_win_rate():
    row = normalize_leaderboard_row({
        "rank": "1",
        "proxyWallet": "0xabc123",
        "userName": "trader",
        "vol": 5173063.79,
        "pnl": 1581705.79,
    })
    assert row["address"] == "0xabc123"
    assert row["user_name"] == "trader"
    assert row["profit"] == pytest.approx(1581705.79)
    assert row["volume"] == pytest.approx(5173063.79)
    assert row["win_rate"] is None
    assert row["trades"] is None
    assert row["avg_size"] is None


def test_normalize_drops_rows_without_address():
    assert normalize_leaderboard_row({"pnl": 10, "vol": 20}) is None
    assert normalize_leaderboard_rows([{"pnl": 1}, {"proxyWallet": "0x1", "pnl": 2}]) == [
        {
            "address": "0x1",
            "user_name": "",
            "profit": 2.0,
            "volume": 0.0,
            "trades": None,
            "win_rate": None,
            "avg_size": None,
            "rank": None,
        }
    ]


def test_data_api_winrate_is_refused_not_mapped_to_pnl():
    with pytest.raises(UnsupportedLeaderboardType, match="does not rank by win rate"):
        data_api_sort_by("winrate")
    assert data_api_sort_by("profit") == "profit"
    assert data_api_sort_by("active") == "volume"
    assert "win rate" in WINRATE_UNSUPPORTED_MESSAGE.lower()


def test_quality_flags_disclose_missing_fields_and_active_alias():
    traders = normalize_leaderboard_rows([
        {"proxyWallet": "0x1", "pnl": 10, "vol": 100},
    ])
    flags = leaderboard_quality_flags("data-api", "active", traders)
    assert "data_api_v1_leaderboard" in flags
    assert "active_ranked_by_volume" in flags
    assert "win_rate_not_provided" in flags
    assert "trade_count_not_provided" in flags


def test_sort_traders_does_not_treat_missing_win_rate_as_zero_edge():
    traders = [
        {"address": "0x1", "profit": 5, "volume": 10, "win_rate": None},
        {"address": "0x2", "profit": 1, "volume": 50, "win_rate": None},
    ]
    by_volume = sort_traders(traders, "volume")
    assert [row["address"] for row in by_volume] == ["0x2", "0x1"]
