"""Realized Spot performance accounting in quote currency (TMN for the challenge)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Fill:
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")
    fee_asset: str = "TMN"


@dataclass(frozen=True)
class PerformanceReport:
    initial_capital: Decimal
    final_cash: Decimal
    realized_pnl: Decimal
    total_fees: Decimal
    open_quantity: Decimal
    return_percent: Decimal

    def to_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in self.__dict__.items()}


def calculate_realized_performance(
    fills: list[Fill], initial_capital: Decimal = Decimal("5000000")
) -> PerformanceReport:
    """Calculate realized FIFO PnL; open coin inventory is reported, not valued."""
    lots: list[tuple[Decimal, Decimal]] = []
    cash = initial_capital
    realized = Decimal("0")
    fees = Decimal("0")
    for fill in fills:
        side = fill.side.upper()
        notional = fill.quantity * fill.price
        quote_fee = fill.fee if fill.fee_asset.upper() in {"TMN", "IRT", "IRR"} else Decimal("0")
        fees += fill.fee
        if side == "BUY":
            cash -= notional + quote_fee
            unit_cost = fill.price + (quote_fee / fill.quantity if fill.quantity else Decimal("0"))
            lots.append((fill.quantity, unit_cost))
            continue
        if side != "SELL":
            raise ValueError(f"Unsupported Spot side: {fill.side}")
        remaining = fill.quantity
        cost = Decimal("0")
        while remaining > 0:
            if not lots:
                raise ValueError("Sell fill exceeds tracked Spot inventory")
            lot_quantity, lot_price = lots[0]
            matched = min(remaining, lot_quantity)
            cost += matched * lot_price
            remaining -= matched
            lot_quantity -= matched
            if lot_quantity == 0:
                lots.pop(0)
            else:
                lots[0] = (lot_quantity, lot_price)
        cash += notional - quote_fee
        realized += notional - cost - quote_fee
    open_quantity = sum((quantity for quantity, _ in lots), Decimal("0"))
    return PerformanceReport(
        initial_capital=initial_capital,
        final_cash=cash,
        realized_pnl=realized,
        total_fees=fees,
        open_quantity=open_quantity,
        return_percent=((cash - initial_capital) / initial_capital * Decimal("100")),
    )


def fills_from_decision_records(records: list[dict[str, Any]]) -> list[Fill]:
    """Extract executed Spot fills from persisted decision records."""
    fills: list[Fill] = []
    for record in records:
        result = record.get("execution", {}).get("result", {})
        for raw in result.get("fills", []) if isinstance(result, dict) else []:
            fills.append(
                Fill(
                    side=str(record["decision"]["action"]),
                    quantity=Decimal(str(raw["quantity"])),
                    price=Decimal(str(raw["price"])),
                    fee=Decimal(str(raw.get("fee", "0"))),
                    fee_asset=str(raw.get("feeAsset", "TMN")),
                )
            )
    return fills
