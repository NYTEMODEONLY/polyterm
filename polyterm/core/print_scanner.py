"""Verified print ingest from lagged Polymarket Data API trades.

A print is a fill that actually happened. This scanner reads the public
Data API trade/activity surface, not the live CLOB tape. It does not
invent wallets, notionals, prices, or a lag duration.
"""

from datetime import datetime, timezone
from typing import Mapping

from ..api.data_api import DataAPIClient
from ..api.data_api_lag import label_payload, stamp


NON_TRADE_TYPES = frozenset({
    "split",
    "merge",
    "redeem",
    "reward",
    "conversion",
    "liquidity",
    "deposit",
    "withdrawal",
})

TRADE_TYPES = frozenset({
    "",
    "trade",
    "trade_matched",
    "buy",
    "sell",
})


class PrintScanner:
    """Fetch and normalize verified Data API prints."""

    def __init__(self, data_api=None):
        self.data_api = data_api or DataAPIClient()

    def fetch_prints(
        self,
        min_notional=None,
        market=None,
        wallet=None,
        limit=100,
    ):
        """Load recent Data API trade rows and keep real fills only.

        Raises whatever the Data API client raises. An empty page is an
        empty tape, not a synthesized success payload.
        """
        raw_rows = self._request_rows(
            min_notional=min_notional,
            market=market,
            wallet=wallet,
            limit=limit,
        )
        prints = []
        skipped = 0
        for raw in raw_rows:
            normalized = normalize_print(raw)
            if normalized is None:
                skipped += 1
                continue
            prints.append(normalized)

        quality_flags = ["public_trade_rows_only"]
        if skipped:
            quality_flags.append("skipped_non_trade_rows")
        if not raw_rows:
            quality_flags.append("empty_data_api_page")

        return label_payload({
            "fetched": len(raw_rows),
            "skipped": skipped,
            "count": len(prints),
            "prints": prints,
            "quality_flags": quality_flags,
        })

    def scan(
        self,
        min_notional,
        market=None,
        wallet=None,
        limit=20,
    ):
        """Fetch prints and return those that meet the print rule."""
        fetched = self.fetch_prints(
            min_notional=min_notional,
            market=market,
            wallet=wallet,
            limit=max(int(limit or 20) * 5, 100),
        )
        matched = match_prints(
            fetched.get("prints") or [],
            min_notional=min_notional,
            market=market,
            wallet=wallet,
        )
        cap = max(int(limit or 20), 1)
        quality_flags = list(fetched.get("quality_flags") or [])
        return label_payload({
            "min_notional": min_notional,
            "market": market,
            "wallet": wallet,
            "fetched": fetched.get("fetched", 0),
            "skipped": fetched.get("skipped", 0),
            "matched": len(matched),
            "prints": matched[:cap],
            "quality_flags": quality_flags,
        })

    def _request_rows(self, min_notional, market, wallet, limit):
        fetch_limit = max(1, min(int(limit or 100), 1000))
        if wallet:
            payload = self.data_api.get_trades(
                address=wallet,
                limit=fetch_limit,
                market=market,
            )
        elif market:
            payload = self.data_api.get_trades(
                limit=fetch_limit,
                market=market,
            )
        else:
            kwargs = {
                "limit": fetch_limit,
                "taker_only": True,
            }
            if min_notional is not None:
                kwargs["filter_type"] = "CASH"
                kwargs["filter_amount"] = min_notional
            payload = self.data_api.get_recent_trades(**kwargs)
        return _as_trade_rows(payload)


def normalize_print(raw):
    """Return a lagged print dict, or None when the row is not a real trade.

    Missing fields are omitted. Nothing is synthesized.
    """
    if not isinstance(raw, Mapping):
        return None

    type_value = str(raw.get("type") or raw.get("activityType") or "").strip().lower()
    if type_value in NON_TRADE_TYPES:
        return None

    size = _optional_float(raw.get("size"))
    price = _optional_float(raw.get("price"))
    usdc_size = _optional_float(raw.get("usdcSize") or raw.get("usdc_size"))
    tx_hash = _optional_text(
        raw.get("transactionHash") or raw.get("transaction_hash") or raw.get("tx_hash")
    )
    side = _optional_text(raw.get("side"))

    notional = None
    if size is not None and price is not None:
        notional = size * price
    elif usdc_size is not None:
        notional = usdc_size

    looks_like_fill = (
        size is not None
        or price is not None
        or notional is not None
        or tx_hash is not None
    )
    if not looks_like_fill:
        return None
    if type_value and type_value not in TRADE_TYPES:
        if tx_hash is None and (size is None or price is None):
            return None

    print_row = {}

    timestamp = raw.get("timestamp")
    if timestamp is None or timestamp == "":
        timestamp = raw.get("matchTime") or raw.get("createdAt")
    if timestamp is not None and timestamp != "":
        print_row["timestamp"] = timestamp
        timestamp_iso = _timestamp_iso(timestamp)
        if timestamp_iso:
            print_row["timestamp_iso"] = timestamp_iso

    wallet = _optional_text(
        raw.get("proxyWallet") or raw.get("user") or raw.get("wallet") or raw.get("trader")
    )
    if wallet:
        print_row["wallet"] = wallet
    if side:
        print_row["side"] = side
    if size is not None:
        print_row["size"] = size
    if price is not None:
        print_row["price"] = price
    if notional is not None:
        print_row["notional"] = notional

    identifiers = (
        ("condition_id", raw.get("conditionId") or raw.get("condition_id")),
        ("market_slug", raw.get("slug") or raw.get("market_slug")),
        ("event_slug", raw.get("eventSlug") or raw.get("event_slug")),
        ("asset", raw.get("asset")),
        ("market_id", raw.get("market") or raw.get("market_id") or raw.get("marketId")),
        ("market_title", raw.get("title") or raw.get("market_title")),
        ("outcome", raw.get("outcome")),
        ("transaction_hash", tx_hash),
    )
    for key, value in identifiers:
        text = _optional_text(value)
        if text:
            print_row[key] = text

    return stamp(print_row)


def match_prints(prints, min_notional, market=None, wallet=None):
    """Keep prints that meet min notional and optional market/wallet filters."""
    matched = []
    for row in prints or []:
        if not isinstance(row, Mapping):
            continue
        notional = row.get("notional")
        if notional is None:
            continue
        try:
            if float(notional) < float(min_notional):
                continue
        except (TypeError, ValueError):
            continue
        if market and not _market_matches(row, market):
            continue
        if wallet and not _wallet_matches(row, wallet):
            continue
        matched.append(row)
    return matched


def print_message(print_row, min_notional=None):
    """Human message from fields that are actually present."""
    parts = ["Lagged Data API print"]
    notional = print_row.get("notional")
    if notional is not None:
        try:
            parts.append("${:,.0f}".format(float(notional)))
        except (TypeError, ValueError):
            pass
    side = print_row.get("side")
    if side:
        parts.append(str(side))
    market = (
        print_row.get("market_title")
        or print_row.get("market_slug")
        or print_row.get("market_id")
        or print_row.get("condition_id")
    )
    if market:
        parts.append("on {}".format(market))
    wallet = print_row.get("wallet")
    if wallet:
        parts.append("wallet {}".format(_short_wallet(wallet)))
    if min_notional is not None:
        try:
            parts.append("(min ${:,.0f})".format(float(min_notional)))
        except (TypeError, ValueError):
            pass
    return " ".join(parts)


def _request_error_message(payload):
    if isinstance(payload, Mapping):
        error = payload.get("error") or payload.get("message")
        if error:
            return str(error)
    return "Data API trades response was not a list of prints"


def _as_trade_rows(payload):
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        for key in ("trades", "data", "activity"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        raise RuntimeError(_request_error_message(payload))
    raise TypeError("Data API trades response was not a list of prints")


def _optional_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    return text


def _timestamp_iso(value):
    """Convert a given timestamp when it is already parseable. Never uses now()."""
    if isinstance(value, datetime):
        parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        as_float = float(text)
        if as_float > 1e9:
            return datetime.fromtimestamp(as_float, timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.isoformat()
    except ValueError:
        return None


def _market_matches(print_row, market):
    needle = str(market).strip().lower()
    if not needle:
        return True
    candidates = [
        print_row.get("condition_id"),
        print_row.get("market_slug"),
        print_row.get("event_slug"),
        print_row.get("asset"),
        print_row.get("market_id"),
        print_row.get("market_title"),
    ]
    for item in candidates:
        if item is not None and str(item).strip().lower() == needle:
            return True
    return False


def _wallet_matches(print_row, wallet):
    have = print_row.get("wallet")
    if have is None:
        return False
    return str(have).strip().lower() == str(wallet).strip().lower()


def _short_wallet(wallet):
    text = str(wallet)
    if len(text) <= 12:
        return text
    return text[:10] + "..."
