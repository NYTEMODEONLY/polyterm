"""Live-intelligence agent tool normalization tests with mocked clients."""

from polyterm.agent.mcp.tools import flips, live


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


class FakeFlipGamma:
    def get_markets(self, **kwargs):
        return [
            {
                "id": "1",
                "slug": "market-a",
                "question": "Market A",
                "conditionId": "condition-a",
                "clobTokenIds": ["token-a", "token-a-no"],
                "volume24hr": 1000,
                "liquidity": 500,
            },
            {
                "id": "2",
                "slug": "market-b",
                "question": "Market B",
                "conditionId": "condition-b",
                "clobTokenIds": ["token-b", "token-b-no"],
                "volume24hr": 2000,
                "liquidity": 1000,
            },
        ]

    def close(self):
        pass


class FakeFlipCLOB:
    def __init__(self):
        self.history_calls = []

    def get_price_history(self, token_id, interval="1h", fidelity=60, start_ts=None, end_ts=None):
        self.history_calls.append({
            "token_id": token_id,
            "interval": interval,
            "fidelity": fidelity,
            "start_ts": start_ts,
            "end_ts": end_ts,
        })
        if token_id == "token-a":
            return [
                {"t": start_ts + 60, "p": "0.42"},
                {"t": start_ts + 120, "p": "0.51"},
                {"t": end_ts - 60, "p": "0.74"},
            ]
        return [
            {"t": start_ts + 60, "p": "0.70"},
            {"t": end_ts - 60, "p": "0.64"},
        ]

    def get_order_book(self, token_id, depth=20):
        return {
            "bids": [{"price": "0.73"}, {"price": "0.72"}],
            "asks": [{"price": "0.75"}, {"price": "0.76"}],
        }

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
    assert payload["data"]["lag"] is True
    assert payload["data"]["lagged"] is True
    assert "lagged_data_api" in payload["data"]["quality_flags"]
    assert "live_data_api_trades" not in payload["data"]["quality_flags"]


def test_top_traders_calculates_closed_position_win_rate(monkeypatch):
    monkeypatch.setattr(live, "DataAPIClient", lambda: FakeDataAPI())
    monkeypatch.setattr(live.time, "time", lambda: 2100)
    payload = live.top_traders(limit=1, hours=1, min_win_rate=0.6)
    assert payload["success"] is True
    assert payload["data"]["traders"][0]["win_rate"] == 2 / 3
    assert payload["data"]["lagged"] is True
    assert "lagged_data_api" in payload["data"]["quality_flags"]
    assert "live_data_api_trades" not in payload["data"]["quality_flags"]


def test_market_movers_flags_flips(monkeypatch):
    monkeypatch.setattr(live, "GammaClient", lambda: FakeGamma())
    payload = live.market_movers(limit=1, min_abs_change=0.05)
    assert payload["success"] is True
    assert payload["data"]["markets"][0]["flipped_50_percent"] is True


def test_market_flips_detects_crossing_with_explicit_clob_window(monkeypatch):
    fake_clob = FakeFlipCLOB()
    monkeypatch.setattr(flips, "GammaClient", lambda: FakeFlipGamma())
    monkeypatch.setattr(flips, "CLOBClient", lambda: fake_clob)

    payload = flips.market_flips(hours=72, limit=3, direction="above", sample_size=10)

    assert payload["success"] is True
    assert payload["data"]["count"] == 1
    row = payload["data"]["markets"][0]
    assert row["gamma_market_id"] == "1"
    assert row["crossing_direction"] == "above"
    assert row["start_price"] == 0.42
    assert row["end_price"] == 0.74
    assert row["absolute_change"] == 0.32
    assert row["spread"] == 0.02
    assert "explicit_start_end_window" in row["quality_flags"]
    assert fake_clob.history_calls[0]["interval"] == "max"
    assert fake_clob.history_calls[0]["fidelity"] == 3600
    assert fake_clob.history_calls[0]["start_ts"] is not None
    assert fake_clob.history_calls[0]["end_ts"] is not None
