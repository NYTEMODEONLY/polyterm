"""Seeded random strategy simulation. This is not historical backtesting."""

import hashlib
import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List


DEMO_MODE = "demo_random_simulation"
DEMO_DISCLOSURE = (
    "DEMO SIMULATION: this does not replay historical Polymarket trades, "
    "order books, or prices. Entries, exits, and P&L are generated with a "
    "seeded random number generator. Do not use these metrics to choose a strategy."
)


def demo_seed(strategy: str) -> int:
    """Stable seed so a given strategy name is reproducible across processes."""
    digest = hashlib.md5(str(strategy).encode("utf-8")).hexdigest()
    return 42 + int(digest[:8], 16)


def run_demo_simulation(
    markets: List[Dict[str, Any]],
    strategy: str,
    days: int,
    capital: float,
    position_size: float,
) -> Dict[str, Any]:
    """Run a seeded random strategy simulation over current market snapshots.

    Markets are used only as labels and a starting price hint. Trade direction,
    path, and outcomes are synthetic.
    """
    trades: List[Dict[str, Any]] = []
    equity = capital
    equity_curve = [capital]
    peak = capital
    max_drawdown = 0.0
    returns: List[float] = []

    num_trades = min(max(days // 3, 0), 30)
    rng = random.Random(demo_seed(strategy))
    market_pool = markets or [{"question": "DEMO market", "title": "DEMO market", "tokens": []}]

    for i in range(num_trades):
        market = rng.choice(market_pool)
        market_title = str(market.get("question", market.get("title", "")))[:30] or "DEMO market"

        base_price = 0.5
        for token in market.get("tokens") or []:
            if str(token.get("outcome", "")).upper() == "YES":
                try:
                    base_price = float(token.get("price", 0.5))
                except (TypeError, ValueError):
                    pass
                break

        entry_price = max(0.1, min(0.9, base_price + rng.uniform(-0.15, 0.15)))
        side = _demo_side(strategy, entry_price, rng)
        edge = {
            "momentum": 0.02,
            "mean-reversion": 0.015,
            "whale-follow": 0.025,
            "contrarian": 0.01,
            "volume-spike": 0.03,
        }.get(strategy, 0.0)

        win = rng.random() < (0.5 + edge)
        move = rng.uniform(0.02, 0.15)
        if side == "BUY":
            exit_price = entry_price + move if win else entry_price - move
        else:
            exit_price = entry_price - move if win else entry_price + move
        exit_price = max(0.05, min(0.95, exit_price))

        trade_size = equity * position_size
        if side == "BUY":
            pnl = trade_size * ((exit_price - entry_price) / entry_price)
        else:
            pnl = trade_size * ((entry_price - exit_price) / entry_price)

        equity += pnl
        equity_curve.append(equity)
        if equity > peak:
            peak = equity
        drawdown = ((peak - equity) / peak) * 100 if peak else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        returns.append(pnl / trade_size if trade_size > 0 else 0)

        step = days // num_trades if num_trades else 0
        trade_date = (datetime.now() - timedelta(days=days - (i * step))).strftime("%Y-%m-%d")
        trades.append({
            "date": trade_date,
            "market": market_title,
            "side": side,
            "entry": entry_price,
            "exit": exit_price,
            "pnl": pnl,
        })

    winning = [t for t in trades if t["pnl"] > 0]
    losing = [t for t in trades if t["pnl"] < 0]
    avg_win = sum(t["pnl"] for t in winning) / len(winning) if winning else 0
    avg_loss = abs(sum(t["pnl"] for t in losing) / len(losing)) if losing else 1
    total_wins = sum(t["pnl"] for t in winning)
    total_losses = abs(sum(t["pnl"] for t in losing))

    if returns:
        avg_return = sum(returns) / len(returns)
        std_return = (
            math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
            if len(returns) > 1 else 1
        )
        sharpe = (avg_return * math.sqrt(252)) / std_return if std_return > 0 else 0
    else:
        sharpe = 0

    return {
        "mode": DEMO_MODE,
        "uses_historical_data": False,
        "method": "seeded_random_simulation",
        "disclosure": DEMO_DISCLOSURE,
        "final_capital": equity,
        "total_trades": len(trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": (len(winning) / len(trades) * 100) if trades else 0,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": (total_wins / total_losses) if total_losses > 0 else None,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
        "trades": trades,
        "equity_curve": equity_curve,
    }


def _demo_side(strategy: str, entry_price: float, rng: random.Random) -> str:
    if strategy == "momentum":
        return "BUY" if rng.uniform(-0.1, 0.1) > 0 else "SELL"
    if strategy == "mean-reversion":
        if entry_price < 0.35:
            return "BUY"
        if entry_price > 0.65:
            return "SELL"
        return rng.choice(["BUY", "SELL"])
    if strategy == "whale-follow":
        return "BUY" if rng.random() > 0.45 else "SELL"
    if strategy == "contrarian":
        return "SELL" if entry_price > 0.5 else "BUY"
    return rng.choice(["BUY", "SELL"])
