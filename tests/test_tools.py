from decimal import Decimal

from wallex_trading_agent.tools import calculate_spot_position_size


def test_spot_position_tool_applies_both_caps() -> None:
    quantity = calculate_spot_position_size.invoke(
        {
            "available_quote": "5000000",
            "risk_fraction": "0.005",
            "max_position_fraction": "0.10",
            "stop_distance": "1000",
            "entry_price": "100000",
        }
    )

    assert Decimal(quantity) == Decimal("5")
