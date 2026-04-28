"""Polymarket CLOB V2 fee helpers."""

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class FeeSchedule:
    """Protocol fee schedule for a market."""

    rate: float
    exponent: float = 1.0
    taker_only: bool = True
    source: str = "unknown"


GENERIC_FEE_SCHEDULE = FeeSchedule(
    rate=0.05,
    exponent=1.0,
    taker_only=True,
    source="generic",
)
ZERO_FEE_SCHEDULE = FeeSchedule(
    rate=0.0,
    exponent=1.0,
    taker_only=True,
    source="market",
)


def fee_schedule_from_market(market: Optional[Dict[str, Any]]) -> FeeSchedule:
    """Extract the CLOB V2 fee schedule from a Gamma market response."""
    if not market:
        return GENERIC_FEE_SCHEDULE

    if market.get("feesEnabled") is False:
        return ZERO_FEE_SCHEDULE

    schedule = market.get("feeSchedule")
    if isinstance(schedule, str):
        try:
            schedule = json.loads(schedule)
        except (json.JSONDecodeError, TypeError):
            schedule = None

    if isinstance(schedule, dict):
        try:
            return FeeSchedule(
                rate=float(schedule.get("rate", 0) or 0),
                exponent=float(schedule.get("exponent", 1) or 1),
                taker_only=bool(schedule.get("takerOnly", True)),
                source="market",
            )
        except (ValueError, TypeError):
            pass

    taker_base_fee = market.get("takerBaseFee", market.get("taker_base_fee"))
    if taker_base_fee is not None:
        try:
            return FeeSchedule(
                rate=float(taker_base_fee) / 10000.0,
                exponent=1.0,
                taker_only=True,
                source="market",
            )
        except (ValueError, TypeError):
            pass

    return GENERIC_FEE_SCHEDULE


def fee_schedule_from_clob_fee_rate(fee_rate: Optional[Dict[str, Any]]) -> FeeSchedule:
    """Build a schedule from CLOB /fee-rate output."""
    if not fee_rate:
        return GENERIC_FEE_SCHEDULE

    base_fee = fee_rate.get("base_fee")
    try:
        return FeeSchedule(
            rate=float(base_fee) / 10000.0,
            exponent=1.0,
            taker_only=True,
            source="clob",
        )
    except (ValueError, TypeError):
        return GENERIC_FEE_SCHEDULE


def effective_taker_fee_rate(price: float, schedule: Optional[FeeSchedule] = None) -> float:
    """Estimate the CLOB V2 taker fee rate for a trade price."""
    schedule = schedule or GENERIC_FEE_SCHEDULE
    bounded_price = min(max(float(price or 0), 0.0), 1.0)
    fee_curve = bounded_price * (1.0 - bounded_price)
    return max(schedule.rate * (fee_curve ** schedule.exponent), 0.0)


def estimate_taker_fee(amount: float, price: float, schedule: Optional[FeeSchedule] = None) -> float:
    """Estimate the protocol taker fee for a notional trade amount."""
    return max(float(amount or 0), 0.0) * effective_taker_fee_rate(price, schedule)


def breakeven_price(entry_price: float, schedule: Optional[FeeSchedule] = None) -> float:
    """Estimate the price needed to cover entry plus protocol taker fee."""
    entry = min(max(float(entry_price or 0), 0.0), 1.0)
    fee_rate = effective_taker_fee_rate(entry, schedule)
    return min(entry * (1.0 + fee_rate), 1.0)


def fee_source_label(schedule: Optional[FeeSchedule]) -> str:
    """Return a short display label for the fee source."""
    if not schedule:
        return "generic protocol estimate"
    if schedule.source == "market":
        return "market fee schedule"
    if schedule.source == "clob":
        return "CLOB fee-rate endpoint"
    return "generic protocol estimate"
