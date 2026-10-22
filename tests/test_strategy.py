from decimal import Decimal

from wallex_trading_agent.models import Candle, MarketSnapshot
from wallex_trading_agent.strategy import propose


def test_strategy_holds_with_too_little_history() -> None:
    candle = Candle(1, Decimal("1"), Decimal("2"), Decimal("1"), Decimal("1.5"), Decimal("10"))
    snapshot = MarketSnapshot("BTCUSDT", Decimal("1"), Decimal("2"), [candle] * 10)

    decision = propose(snapshot)

    assert decision.action == "HOLD"
    assert decision.quantity == 0


def test_strategy_calculates_indicators_with_valid_history() -> None:
    candles = [
        Candle(
            index,
            Decimal(str(index)),
            Decimal(str(index + 2)),
            Decimal(str(index - 1)),
            Decimal(str(index + 1)),
            Decimal("10"),
        )
        for index in range(1, 60)
    ]
    snapshot = MarketSnapshot("BTCUSDT", Decimal("60"), Decimal("61"), candles)

    decision = propose(snapshot)

    assert "atr" in decision.signal_values
