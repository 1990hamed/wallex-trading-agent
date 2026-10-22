"""Deterministic Spot backtest using the production strategy and realized accounting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from wallex_trading_agent.models import Candle, MarketSnapshot
from wallex_trading_agent.performance import Fill, PerformanceReport, calculate_realized_performance
from wallex_trading_agent.strategy import propose


@dataclass(frozen=True)
class BacktestResult:
    report: PerformanceReport
    trade_count: int
    fills: list[Fill]


def run_backtest(
    candles: list[Candle],
    *,
    symbol: str = "BTCTMN",
    initial_capital: Decimal = Decimal("5000000"),
    max_position_fraction: Decimal = Decimal("0.10"),
    fee_fraction: Decimal = Decimal("0.001"),
) -> BacktestResult:
    """Simulate close-price Spot entries/exits; open inventory is excluded from return."""
    fills: list[Fill] = []
    position = Decimal("0")
    warmup = 50
    for index in range(warmup, len(candles)):
        window = candles[: index + 1]
        close = window[-1].close
        snapshot = MarketSnapshot(symbol, close, close, window)
        decision = propose(snapshot)
        if decision.action == "BUY" and position == 0:
            quantity = (initial_capital * max_position_fraction) / close
            fills.append(Fill("BUY", quantity, close, quantity * close * fee_fraction))
            position = quantity
        elif decision.action == "SELL" and position > 0:
            fills.append(Fill("SELL", position, close, position * close * fee_fraction))
            position = Decimal("0")
    return BacktestResult(
        report=calculate_realized_performance(fills, initial_capital),
        trade_count=len(fills),
        fills=fills,
    )
