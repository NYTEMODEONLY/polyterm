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


def whales(min_notional: float = 10000, hours: int = 24) -> dict:
    engine = WalletIntelligence(database=Database())
    return envelope(engine.local_whales(min_notional=min_notional, hours=hours), meta={"tool": "wallet.whales"})
