from decimal import Decimal

from wallex_trading_agent.backtest import run_backtest
from wallex_trading_agent.models import Candle


def test_backtest_returns_realized_report() -> None:
    candles = [
        Candle(i, Decimal(i), Decimal(i + 2), Decimal(i - 1), Decimal(i + 1), Decimal("10"))
        for i in range(1, 80)
    ]

    result = run_backtest(candles, initial_capital=Decimal("1000"))

    assert result.report.initial_capital == Decimal("1000")
    assert result.report.open_quantity >= 0
