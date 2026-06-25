"""Alert tools for agent adapters."""

from ...contracts import envelope, error_envelope
from ....core.alert_engine import AlertEngine
from ....db.database import Database


def create_price_rule(
    market: str,
    above: float = None,
    below: float = None,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    if not dry_run and not confirm:
        preview = AlertEngine(database=Database()).create_price_rule(
            market=market,
            above=above,
            below=below,
            dry_run=True,
        )
        return error_envelope(
            "alerts.create_price_rule mutates local SQLite state; pass confirm=true to create it",
            data=preview,
            meta={"tool": "alerts.create_price_rule"},
        )

    engine = AlertEngine(database=Database())
    return envelope(
        engine.create_price_rule(market=market, above=above, below=below, dry_run=dry_run),
        meta={"tool": "alerts.create_price_rule"},
    )
