"""Tests for portfolio command field normalization helpers."""

from polyterm.cli.commands.portfolio import _extract_position_fields


def test_extract_position_fields_supports_lowercase_l_pnl_keys():
    """Should handle Data API payloads using realizedPnl/unrealizedPnl keys."""
    normalized = _extract_position_fields(
        {
            "market": "m1",
            "title": "Market 1",
            "side": "yes",
            "size": 10,
            "averagePrice": 0.4,
            "currentValue": 5,
            "realizedPnl": "12.5",
            "unrealizedPnl": "-2.5",
        }
    )

    assert normalized["total_pnl"] == 10.0


def test_extract_position_fields_prefers_explicit_pnl_when_present():
    """Should use explicit pnl field over realized/unrealized variants."""
    normalized = _extract_position_fields(
        {
            "market": "m2",
            "pnl": "42.0",
            "realizedPnl": "10",
            "unrealizedPnl": "5",
        }
    )

    assert normalized["total_pnl"] == 42.0
