"""Tests for market.explain_move recent price movement explanations."""

from polyterm.core.market_move import MarketMoveExplainer


class FakeGammaClient:
    def __init__(self):
        self.queries = []

    def get_market(self, identifier):
        self.queries.append(("get", identifier))
        return {
            "id": "2362221",
            "slug": "bitcoin-above-66k-on-june-2-2026",
            "conditionId": "condition-1",
            "clobTokenIds": ["token-yes", "token-no"],
            "question": "Bitcoin above $66K on June 2?",
            "outcomePrices": ["0.72", "0.28"],
            "volume24hr": 250000,
            "liquidity": 500000,
        }

    def search_markets(self, query, limit=5):
        self.queries.append(("search", query, limit))
        return []


class FakeClobClient:
    def __init__(self):
        self.history_calls = []
        self.book_calls = []

    def get_price_history(self, token_id, interval="1h", fidelity=60):
        self.history_calls.append({"token_id": token_id, "interval": interval, "fidelity": fidelity})
        return [
            {"t": 1717347600, "p": "0.61"},
            {"t": 1717351200, "p": "0.66"},
            {"t": 1717354800, "p": "0.72"},
        ]

    def get_order_book(self, token_id, depth=20):
        self.book_calls.append({"token_id": token_id, "depth": depth})
        return {
            "bids": [{"price": "0.71", "size": "1200"}],
            "asks": [{"price": "0.73", "size": "900"}],
        }


def test_market_move_explainer_summarizes_direction_magnitude_and_drivers():
    clob = FakeClobClient()
    explainer = MarketMoveExplainer(gamma_client=FakeGammaClient(), clob_client=clob)

    result = explainer.explain("bitcoin", hours=24)

    assert result["query"] == "bitcoin"
    assert result["market"]["gamma_market_id"] == "2362221"
    assert result["market"]["condition_id"] == "condition-1"
    assert result["move"] == {
        "direction": "up",
        "start_price": 0.61,
        "end_price": 0.72,
        "absolute_change": 0.11,
        "relative_change": 0.1803,
        "hours": 24,
        "points": 3,
    }
    assert result["headline"] == "YES moved up 11.0 points over 24h."
    assert "Price history shows a 11.0 point YES move from 61.0% to 72.0%." in result["drivers"]
    assert "Current order book spread is 2.0 points, so the move is backed by a tradable CLOB quote." in result["drivers"]
    assert result["quality_flags"] == ["price_history_available", "orderbook_available", "no_trade_execution"]
    assert clob.history_calls == [{"token_id": "token-yes", "interval": "1h", "fidelity": 60}]
    assert clob.book_calls == [{"token_id": "token-yes", "depth": 20}]


def test_market_move_explainer_reports_missing_price_history_as_gap():
    class EmptyHistoryClob(FakeClobClient):
        def get_price_history(self, token_id, interval="1h", fidelity=60):
            return []

    explainer = MarketMoveExplainer(gamma_client=FakeGammaClient(), clob_client=EmptyHistoryClob())

    result = explainer.explain("bitcoin")

    assert result["move"]["direction"] == "unknown"
    assert result["move"]["points"] == 0
    assert "price_history_unavailable" in result["quality_flags"]
    assert "Price history unavailable; cannot attribute a recent move." in result["caveats"]
