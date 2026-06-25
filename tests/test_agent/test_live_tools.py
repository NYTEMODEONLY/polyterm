"""Live-intelligence agent tool normalization tests with mocked clients."""

from polyterm.agent.mcp.tools import live


class FakeGamma:
    def get_trending_markets(self, limit):
        return [
            {"id": "1", "question": "A", "volume24hr": 10, "liquidity": 1, "outcomePrices": '["0.4","0.6"]'},
            {"id": "2", "question": "B", "volume24hr": 30, "liquidity": 2, "outcomePrices": '["0.7","0.3"]'},
        ]

    def get_markets(self, **kwargs):
        return [
            {"id": "1", "question": "A", "volume24hr": 10, "oneDayPriceChange": 0.2, "outcomePrices": '["0.6","0.4"]'},
            {"id": "2", "question": "B", "volume24hr": 30, "oneDayPriceChange": 0.01, "outcomePrices": '["0.7","0.3"]'},
        ]

    def close(self):
        pass


class FakeDataAPI:
    def get_trades(self, limit):
        return [
            {
                "proxyWallet": "0xabc",
                "size": 100,
                "price": 0.5,
                "timestamp": 2000,
                "title": "Market A",
                "slug": "market-a",
                "conditionId": "0x1",
            },
            {
                "proxyWallet": "0xdef",
                "size": 10,
                "price": 0.1,
                "timestamp": 2000,
                "title": "Market B",
                "conditionId": "0x2",
            },
        ]

    def get_leaderboard(self, period, limit, sort_by):
        return []

    def get_closed_positions(self, address, limit=50, sort_by="REALIZEDPNL", offset=0):
        return [
            {"timestamp": 2000, "realizedPnl": 1},
            {"timestamp": 2000, "realizedPnl": 2},
            {"timestamp": 2000, "realizedPnl": -1},
        ]

    def close(self):
        pass


def test_top_markets_uses_live_gamma_shape(monkeypatch):
    monkeypatch.setattr(live, "GammaClient", lambda: FakeGamma())
    payload = live.top_markets(limit=1)
    assert payload["success"] is True
    assert payload["data"]["markets"][0]["gamma_market_id"] == "2"


def test_whale_trades_filters_by_notional(monkeypatch):
    monkeypatch.setattr(live, "DataAPIClient", lambda: FakeDataAPI())
    monkeypatch.setattr(live.time, "time", lambda: 2100)
    payload = live.whale_trades(limit=5, hours=1, min_notional=10)
    assert payload["success"] is True
    assert len(payload["data"]["trades"]) == 1
    assert payload["data"]["trades"][0]["wallet"] == "0xabc"


def test_top_traders_calculates_closed_position_win_rate(monkeypatch):
    monkeypatch.setattr(live, "DataAPIClient", lambda: FakeDataAPI())
    monkeypatch.setattr(live.time, "time", lambda: 2100)
    payload = live.top_traders(limit=1, hours=1, min_win_rate=0.6)
    assert payload["success"] is True
    assert payload["data"]["traders"][0]["win_rate"] == 2 / 3


def test_market_movers_flags_flips(monkeypatch):
    monkeypatch.setattr(live, "GammaClient", lambda: FakeGamma())
    payload = live.market_movers(limit=1, min_abs_change=0.05)
    assert payload["success"] is True
    assert payload["data"]["markets"][0]["flipped_50_percent"] is True
