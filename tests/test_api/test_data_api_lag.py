"""Unit tests for lagged Data API labels. No live network."""

from polyterm.api.data_api_lag import (
    DISCLOSURE,
    QUALITY_FLAG,
    SOURCE,
    is_lagged_payload,
    label_payload,
    metadata,
    stamp,
    table_title,
    with_quality_flag,
)


def test_metadata_marks_data_api_as_lagged_without_duration():
    fields = metadata()
    assert fields["source"] == SOURCE
    assert fields["lag"] is True
    assert fields["lagged"] is True
    assert "duration" not in fields
    assert "lag_ms" not in fields
    assert "lag_seconds" not in fields


def test_disclosure_says_lagged_not_live_clob_without_inventing_duration():
    text = DISCLOSURE.lower()
    assert "lagged" in text
    assert "not live clob" in text
    assert "data-api.polymarket.com" in text
    for token in ("minute", "second", "hour", "ms", "delay of"):
        assert token not in text


def test_stamp_fills_source_and_keeps_nested_source_map():
    nested = stamp({"source": {"positions": "data-api", "trades": "data-api"}})
    assert nested["lag"] is True
    assert nested["lagged"] is True
    assert nested["source"] == {"positions": "data-api", "trades": "data-api"}

    filled = stamp({"positions": []})
    assert filled["source"] == "data_api"
    assert filled["lagged"] is True


def test_with_quality_flag_replaces_live_misnomer():
    flags = with_quality_flag(["live_data_api_trades", "public_trade_rows_only"])
    assert flags[0] == QUALITY_FLAG
    assert "live_data_api_trades" not in flags
    assert "public_trade_rows_only" in flags


def test_label_payload_and_table_title():
    payload = label_payload({"wallets": []}, quality_flags=["public_data_api"])
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert payload["source"] == "data_api"
    assert QUALITY_FLAG in payload["quality_flags"]
    assert is_lagged_payload(payload)
    assert table_title("Positions") == "Positions — lagged Data API (not live CLOB)"
