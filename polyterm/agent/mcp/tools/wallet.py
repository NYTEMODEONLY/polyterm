"""Wallet tools for agent adapters."""

from ...contracts import envelope
from ....api.data_api import DataAPIClient
from ....core.wallet_intelligence import WalletIntelligence
from ....db.database import Database


def inspect(address: str, limit: int = 100) -> dict:
    data_api = DataAPIClient()
    engine = WalletIntelligence(data_api=data_api, database=Database())
    try:
        return envelope(engine.analyze_wallet(address, limit=limit), meta={"tool": "wallet.inspect"})
    finally:
        data_api.close()


def whales(min_notional: float = 10000, hours: int = 24, limit: int = 20) -> dict:
    data_api = DataAPIClient()
    engine = WalletIntelligence(data_api=data_api, database=Database())
    try:
        return envelope(
            engine.live_whales(min_notional=min_notional, hours=hours, limit=limit),
            meta={"tool": "wallet.whales"},
        )
    finally:
        data_api.close()


def whale_trades(limit: int = 3, hours: int = 48, min_notional: float = 10000, sample_size: int = 3000) -> dict:
    data_api = DataAPIClient()
    engine = WalletIntelligence(data_api=data_api, database=Database())
    try:
        return envelope(
            engine.whale_trades(
                min_notional=min_notional,
                hours=hours,
                limit=limit,
                sample_size=sample_size,
            ),
            meta={"tool": "wallet.whale_trades"},
        )
    finally:
        data_api.close()


def smart_money(min_win_rate: float = 0.70, min_trades: int = 10, limit: int = 20) -> dict:
    engine = WalletIntelligence(database=Database())
    return envelope(
        engine.smart_money(min_win_rate=min_win_rate, min_trades=min_trades, limit=limit),
        meta={"tool": "wallet.smart_money"},
    )
