from datetime import datetime, timedelta, timezone

from polyterm.core.wallet_intelligence import WalletIntelligence


class FakeDataAPI:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get_recent_trades(self, limit=1000, offset=0, **kwargs):
        self.calls.append({"limit": limit, "offset": offset, **kwargs})
        return self.pages.get(offset, [])


class FailingPageDataAPI(FakeDataAPI):
    def __init__(self, pages, failing_offsets):
        super().__init__(pages)
        self.failing_offsets = set(failing_offsets)

    def get_recent_trades(self, limit=1000, offset=0, **kwargs):
        if offset in self.failing_offsets:
            self.calls.append({"limit": limit, "offset": offset, **kwargs})
            raise RuntimeError(f"timeout at offset {offset}")
        return super().get_recent_trades(limit=limit, offset=offset, **kwargs)


class FakeDatabase:
    def __init__(self):
        self.trades = []
        self.wallets = []

    def get_large_trades(self, min_notional=10000, hours=24):
        return []

    def insert_trade(self, trade):
        self.trades.append(trade)
        return len(self.trades)

    def upsert_wallet(self, wallet):
        self.wallets.append(wallet)

    def get_smart_money_wallets(self, min_win_rate=0.70, min_trades=10):
        return [
            wallet
            for wallet in self.wallets
            if wallet.win_rate >= min_win_rate and wallet.total_trades >= min_trades
        ]


def test_live_whales_returns_public_trades_and_wallet_rollups_by_timeframe():
    now = datetime(2026, 6, 2, 17, 0, 0, tzinfo=timezone.utc)
    recent_ts = int((now - timedelta(hours=2)).timestamp())
    older_ts = int((now - timedelta(hours=80)).timestamp())
    pages = {
        0: [
            {
                "proxyWallet": "0xaaa",
                "side": "BUY",
                "size": 150_000,
                "price": 0.80,
                "timestamp": recent_ts,
                "title": "Fed cuts rates in June?",
                "slug": "fed-cuts-rates-in-june",
                "outcome": "Yes",
                "transactionHash": "0xtrade1",
            },
            {
                "proxyWallet": "0xbbb",
                "side": "SELL",
                "size": 75_000,
                "price": 0.50,
                "timestamp": recent_ts,
                "title": "Below threshold",
                "slug": "below-threshold",
                "outcome": "No",
                "transactionHash": "0xsmall",
            },
            {
                "proxyWallet": "0xccc",
                "side": "BUY",
                "size": 200_000,
                "price": 0.75,
                "timestamp": older_ts,
                "title": "Too old",
                "slug": "too-old",
                "outcome": "Yes",
                "transactionHash": "0xold",
            },
        ],
        1000: [],
    }
    engine = WalletIntelligence(data_api=FakeDataAPI(pages), database=FakeDatabase())

    result = engine.live_whales(min_notional=100_000, hours=72, limit=5, now=now, page_size=1000)

    assert result["source"] == "public_data_api"
    assert result["trade_count"] == 1
    assert result["wallet_count"] == 1
    assert result["trades"][0]["wallet"] == "0xaaa"
    assert result["trades"][0]["notional"] == 120_000
    assert result["wallets"][0]["address"] == "0xaaa"
    assert result["wallets"][0]["notional"] == 120_000
    assert result["quality_flags"] == ["public_data_api", "trade_direction_may_be_inferred"]


def test_live_whales_paginates_public_trades_until_limit_or_cutoff():
    now = datetime(2026, 6, 2, 17, 0, 0, tzinfo=timezone.utc)
    recent_ts = int((now - timedelta(hours=1)).timestamp())
    pages = {
        0: [{"proxyWallet": "0xaaa", "size": 10, "price": 1, "timestamp": recent_ts}],
        1000: [{"proxyWallet": "0xbbb", "size": 200_000, "price": 1, "timestamp": recent_ts}],
        2000: [],
    }
    api = FakeDataAPI(pages)
    engine = WalletIntelligence(data_api=api, database=FakeDatabase())

    result = engine.live_whales(min_notional=100_000, hours=72, limit=5, now=now, page_size=1000)

    assert [call["offset"] for call in api.calls] == [0, 1000, 2000]
    assert api.calls[0]["filter_type"] == "CASH"
    assert api.calls[0]["filter_amount"] == 100_000
    assert result["trade_count"] == 1
    assert result["trades"][0]["wallet"] == "0xbbb"


def test_live_whales_limits_displayed_trades_without_hiding_wallet_rollups():
    now = datetime(2026, 6, 2, 17, 0, 0, tzinfo=timezone.utc)
    recent_ts = int((now - timedelta(hours=1)).timestamp())
    pages = {
        0: [
            {"proxyWallet": "0xaaa", "size": 200_000, "price": 1, "timestamp": recent_ts, "transactionHash": "0x1"},
            {"proxyWallet": "0xaaa", "size": 190_000, "price": 1, "timestamp": recent_ts, "transactionHash": "0x2"},
            {"proxyWallet": "0xbbb", "size": 180_000, "price": 1, "timestamp": recent_ts, "transactionHash": "0x3"},
        ],
        1000: [],
    }
    engine = WalletIntelligence(data_api=FakeDataAPI(pages), database=FakeDatabase())

    result = engine.live_whales(min_notional=100_000, hours=72, limit=2, now=now, page_size=1000)

    assert result["trade_count"] == 3
    assert [trade["wallet"] for trade in result["trades"]] == ["0xaaa", "0xaaa"]
    assert [wallet["address"] for wallet in result["wallets"]] == ["0xaaa", "0xbbb"]


def test_live_whales_logs_public_trade_results_to_local_database():
    now = datetime(2026, 6, 2, 17, 0, 0, tzinfo=timezone.utc)
    recent_ts = int((now - timedelta(hours=1)).timestamp())
    pages = {
        0: [
            {
                "proxyWallet": "0xaaa",
                "side": "BUY",
                "size": 200_000,
                "price": 0.75,
                "timestamp": recent_ts,
                "title": "Fed cuts rates in June?",
                "slug": "fed-cuts-rates-in-june",
                "conditionId": "condition-1",
                "outcome": "Yes",
                "transactionHash": "0xtrade1",
            },
            {
                "proxyWallet": "0xbbb",
                "side": "SELL",
                "size": 150_000,
                "price": 0.80,
                "timestamp": recent_ts,
                "title": "Will BTC hit 80k?",
                "slug": "btc-80k",
                "conditionId": "condition-2",
                "outcome": "No",
                "transactionHash": "0xtrade2",
            },
        ],
        1000: [],
    }
    db = FakeDatabase()
    engine = WalletIntelligence(data_api=FakeDataAPI(pages), database=db)

    result = engine.live_whales(min_notional=100_000, hours=72, limit=1, now=now, page_size=1000)

    assert result["cached_trade_count"] == 2
    assert {trade.tx_hash for trade in db.trades} == {"0xtrade1", "0xtrade2"}
    assert db.trades[0].market_id == "condition-1"
    assert db.trades[0].market_slug == "fed-cuts-rates-in-june"
    assert db.trades[0].wallet_address == "0xaaa"
    assert db.trades[0].notional == 150_000
    assert {wallet.address for wallet in db.wallets} == {"0xaaa", "0xbbb"}
    assert all("whale" in wallet.tags for wallet in db.wallets)


def test_smart_money_returns_ranked_local_wallets_with_thresholds():
    from polyterm.db.models import Wallet

    now = datetime(2026, 6, 1)
    db = FakeDatabase()
    db.wallets = [
        Wallet(address="0xsharp", first_seen=now, total_trades=20, total_volume=250_000, win_rate=0.82, avg_position_size=12_500, largest_trade=50_000, tags=["smart_money"]),
        Wallet(address="0xsmall", first_seen=now, total_trades=9, total_volume=300_000, win_rate=0.91, avg_position_size=33_333, largest_trade=100_000, tags=["whale"]),
        Wallet(address="0xok", first_seen=now, total_trades=15, total_volume=100_000, win_rate=0.75, avg_position_size=6_666, largest_trade=20_000, tags=[]),
    ]
    engine = WalletIntelligence(data_api=FakeDataAPI({}), database=db)

    result = engine.smart_money(min_win_rate=0.70, min_trades=10, limit=5)

    assert result["source"] == "local_db"
    assert result["wallet_count"] == 2
    assert [wallet["address"] for wallet in result["wallets"]] == ["0xsharp", "0xok"]
    assert result["wallets"][0]["edge_score"] > result["wallets"][1]["edge_score"]
    assert result["wallets"][0]["smart_money_score"] > result["wallets"][1]["smart_money_score"]
    assert result["wallets"][0]["ranking_inputs"]["hit_rate"] == 0.82
    assert result["wallets"][0]["ranking_inputs"]["realized_pnl_available"] is False
    assert result["wallets"][0]["is_whale"] is True
    assert result["wallets"][0]["wallet_role"] == "smart_money_whale"
    assert result["wallets"][0]["explanation"]
    assert result["quality_flags"] == ["local_db_smart_money", "requires_recent_refresh_for_live_flow"]


def test_whale_trades_scans_pages_and_ranks_by_notional_not_recency():
    now = datetime(2026, 7, 5, 3, 0, 0, tzinfo=timezone.utc)
    recent_ts = int((now - timedelta(minutes=5)).timestamp())
    older_ts = int((now - timedelta(hours=12)).timestamp())
    pages = {
        0: [
            {
                "proxyWallet": "0xsmall",
                "name": "latest-small",
                "side": "BUY",
                "size": 20_000,
                "price": 0.50,
                "timestamp": recent_ts,
                "title": "Latest smaller trade",
                "slug": "latest-small",
                "eventSlug": "latest-small-event",
                "outcome": "Yes",
                "transactionHash": "0xsmall",
            }
        ],
        1000: [
            {
                "proxyWallet": "0xbig",
                "name": "older-big",
                "side": "SELL",
                "size": 2_500_000,
                "price": 0.53,
                "timestamp": older_ts,
                "title": "Older bigger trade",
                "slug": "older-big",
                "eventSlug": "older-big-event",
                "outcome": "No",
                "transactionHash": "0xbig",
            }
        ],
        2000: [],
    }
    api = FakeDataAPI(pages)
    engine = WalletIntelligence(data_api=api, database=FakeDatabase())

    result = engine.whale_trades(min_notional=10_000, hours=48, limit=2, sample_size=3000, now=now)

    assert [call["offset"] for call in api.calls] == [0, 1000, 2000]
    assert api.calls[0]["filter_type"] == "CASH"
    assert api.calls[0]["filter_amount"] == 10_000
    assert result["trades"][0]["wallet"] == "0xbig"
    assert result["trades"][0]["notional"] == 1_325_000
    assert result["trades"][1]["wallet"] == "0xsmall"
    assert result["rows_scanned"] == 2
    assert result["sample_size"] == 3000
    assert "notional_desc_sorted" in result["quality_flags"]


def test_whale_trades_reports_api_errors_and_window_limits():
    now = datetime(2026, 7, 5, 3, 0, 0, tzinfo=timezone.utc)
    recent_ts = int((now - timedelta(minutes=5)).timestamp())
    api = FailingPageDataAPI(
        {0: [{"proxyWallet": "0xaaa", "size": 20_000, "price": 0.50, "timestamp": recent_ts}]},
        failing_offsets={1000},
    )
    engine = WalletIntelligence(data_api=api, database=FakeDatabase())

    result = engine.whale_trades(min_notional=10_000, hours=48, limit=3, sample_size=3000, now=now)

    assert result["count"] == 1
    assert result["errors"] == [{"offset": 1000, "error": "timeout at offset 1000"}]
    assert "data_api_page_error" in result["quality_flags"]
    assert "data_api_recent_tape_window_limited" in result["quality_flags"]
