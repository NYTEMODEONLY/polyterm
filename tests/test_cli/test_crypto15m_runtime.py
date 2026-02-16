"""Runtime behavior tests for crypto15m market discovery."""

from unittest.mock import Mock

from polyterm.cli.commands.crypto15m import find_15m_markets


def test_find_15m_markets_returns_after_primary_scan():
    """Should stop after primary scan when a 15m match is found."""
    gamma_client = Mock()
    gamma_client.get_markets.return_value = [
        {
            "id": "btc-15m",
            "question": "Will Bitcoin go up in the next 15 minute window?",
            "active": True,
            "closed": False,
        }
    ]

    markets = find_15m_markets(gamma_client, crypto=None)

    assert len(markets) == 1
    assert markets[0]["crypto_symbol"] == "BTC"
    assert gamma_client.get_markets.call_count == 1
    assert gamma_client.get_markets.call_args_list[0].kwargs["limit"] == 300


def test_find_15m_markets_uses_bounded_api_calls_when_empty():
    """Should use at most two market fetches when no matches exist."""
    gamma_client = Mock()
    gamma_client.get_markets.side_effect = [[], []]

    markets = find_15m_markets(gamma_client, crypto=None)

    assert markets == []
    assert gamma_client.get_markets.call_count == 2
    assert gamma_client.get_markets.call_args_list[0].kwargs["limit"] == 300
    assert gamma_client.get_markets.call_args_list[1].kwargs["limit"] == 1000
