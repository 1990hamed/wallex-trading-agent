"""Explicit LangChain tools for deterministic, auditable calculations."""

from decimal import Decimal

from langchain_core.tools import tool


@tool
def calculate_spot_position_size(
    available_quote: str,
    risk_fraction: str,
    max_position_fraction: str,
    stop_distance: str,
    entry_price: str,
) -> str:
    """Return a risk-capped Spot quantity as a decimal string."""
    """Calculate a Spot quantity under risk and allocation caps."""
    balance = Decimal(available_quote)
    risk_size = (balance * Decimal(risk_fraction)) / Decimal(stop_distance)
    position_size = (balance * Decimal(max_position_fraction)) / Decimal(entry_price)
    return str(min(risk_size, position_size))
