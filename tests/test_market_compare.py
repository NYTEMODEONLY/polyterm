"""Tests for agent-native market.compare divergence analysis."""

from polyterm.core.market_compare import MarketComparisonEngine


class FakeGammaClient:
    def __init__(self):
        self.markets = {
            "bitcoin-100k": {
                "id": "1",
                "slug": "bitcoin-100k",
                "question": "Bitcoin above $100k?",
                "conditionId": "cond-1",
                "clobTokenIds": '["yes-1", "no-1"]',
                "outcomePrices": '["0.62", "0.38"]',
                "volume": "1000",
                "liquidity": "500",
                "active": True,
                "closed": False,
            },
            "bitcoin-90k": {
                "id": "2",
                "slug": "bitcoin-90k",
                "question": "Bitcoin above $90k?",
                "conditionId": "cond-2",
                "clobTokenIds": '["yes-2", "no-2"]',
                "outcomePrices": '["0.82", "0.18"]',
                "volume": "4000",
                "liquidity": "1200",
                "active": True,
                "closed": False,
            },
        }

    def get_market(self, identifier):
        if identifier in self.markets:
            return self.markets[identifier]
        raise KeyError(identifier)

    def search_markets(self, query, limit=5):
        return [self.markets[query]] if query in self.markets else []


class FakeCLOBClient:
    def get_price_history(self, token_id, interval="1h", fidelity=60):
        return {
            "yes-1": [{"p": 0.55}, {"p": 0.62}],
            "yes-2": [{"p": 0.85}, {"p": 0.82}],
        }[token_id]

    def get_order_book(self, token_id, depth=20):
        return {
            "yes-1": {"bids": [{"price": "0.61"}], "asks": [{"price": "0.63"}]},
            "yes-2": {"bids": [{"price": "0.81"}], "asks": [{"price": "0.83"}]},
        }[token_id]


def test_compare_returns_structured_market_divergence():
    engine = MarketComparisonEngine(gamma_client=FakeGammaClient(), clob_client=FakeCLOBClient())

    result = engine.compare(["bitcoin-100k", "bitcoin-90k"], hours=24)

    assert result["query"] == ["bitcoin-100k", "bitcoin-90k"]
    assert result["count"] == 2
    assert [market["slug"] for market in result["markets"]] == ["bitcoin-100k", "bitcoin-90k"]
    assert result["markets"][0]["probability"] == 0.62
    assert result["markets"][0]["move"]["absolute_change"] == 0.07
    assert result["pairwise"][0]["probability_gap"] == 0.2
    assert result["pairwise"][0]["liquidity_gap"] == 700.0
    assert result["headline"] == "Compared 2 markets; widest YES gap is 20.0 points."
    assert "price_history_available" in result["quality_flags"]
    assert result["evidence_sources"][0]["source"] == "gamma_api"


def test_compare_requires_at_least_two_markets():
    engine = MarketComparisonEngine(gamma_client=FakeGammaClient(), clob_client=FakeCLOBClient())

    result = engine.compare(["bitcoin-100k"], hours=24)

    assert result["count"] == 1
    assert result["pairwise"] == []
    assert "need_at_least_two_markets" in result["quality_flags"]
