from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

Action = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    best_bid: Decimal
    best_ask: Decimal
    candles: list[Candle]

    @property
    def mid_price(self) -> Decimal:
        return (self.best_bid + self.best_ask) / Decimal("2")


@dataclass(frozen=True)
class TradeDecision:
    action: Action
    confidence: float
    quantity: Decimal
    entry_price: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    reasons: list[str]
    signal_values: dict[str, str]


@dataclass(frozen=True)
class DecisionLog:
    timestamp: str
    mode: str
    symbol: str
    decision: TradeDecision
    risk_approved: bool
    risk_reason: str
    mcp_tools: list[str]
    ai_review: dict[str, object]
    execution: dict[str, object]

    @classmethod
    def create(
        cls,
        *,
        mode: str,
        symbol: str,
        decision: TradeDecision,
        risk_approved: bool,
        risk_reason: str,
        mcp_tools: list[str],
        ai_review: dict[str, object],
        execution: dict[str, object],
    ) -> DecisionLog:
        return cls(
            timestamp=datetime.now(UTC).isoformat(),
            mode=mode,
            symbol=symbol,
            decision=decision,
            risk_approved=risk_approved,
            risk_reason=risk_reason,
            mcp_tools=mcp_tools,
            ai_review=ai_review,
            execution=execution,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
