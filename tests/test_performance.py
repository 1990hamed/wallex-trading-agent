from decimal import Decimal

from wallex_trading_agent.performance import Fill, calculate_realized_performance


def test_realized_fifo_return_in_tmn_includes_fees() -> None:
    report = calculate_realized_performance(
        [
            Fill("BUY", Decimal("1"), Decimal("100"), Decimal("1")),
            Fill("SELL", Decimal("1"), Decimal("120"), Decimal("1")),
        ],
        initial_capital=Decimal("1000"),
    )
    assert report.realized_pnl == Decimal("18")
    assert report.total_fees == Decimal("2")
    assert report.final_cash == Decimal("1018")
    assert report.return_percent == Decimal("1.8")
    assert report.open_quantity == 0
