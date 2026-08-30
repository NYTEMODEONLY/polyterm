"""Tests for the Gamma volume heuristic (not whale identity)."""

from unittest.mock import Mock

from polyterm.core.volume_spikes import (
    EVIDENCE_LEVEL,
    detect_high_volume_markets,
)


def test_detect_high_volume_markets_has_no_trader_identity():
    gamma = Mock()
    gamma.get_markets.return_value = [
        {
            "id": "market1",
            "title": "Test Market 1",
            "volume24hr": 15000.0,
            "outcomePrices": ["0.70", "0.30"],
            "lastTradePrice": 0.70,
        },
        {
            "id": "market2",
            "question": "Test Market 2",
            "volume24hr": 500.0,
            "outcomePrices": ["0.50", "0.50"],
        },
    ]

    markets = detect_high_volume_markets(gamma, min_volume=10000, now=1_700_000_000)
    assert len(markets) == 1
    item = markets[0]
    assert item.market_id == "market1"
    assert item.volume_24hr == 15000.0
    assert item.outcome_lean == "YES"
    assert item.evidence_level == EVIDENCE_LEVEL
    payload = item.to_dict()
    assert "trader" not in payload
    assert payload["evidence_level"] == "gamma_volume24hr_heuristic"
