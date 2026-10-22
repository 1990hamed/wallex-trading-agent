from __future__ import annotations

from decimal import Decimal
from statistics import fmean

from wallex_trading_agent.models import Action, MarketSnapshot, TradeDecision


def _ema(values: list[float], period: int) -> float:
    alpha = 2 / (period + 1)
    value = values[0]
    for close in values[1:]:
        value = (close * alpha) + (value * (1 - alpha))
    return value


def _rsi(closes: list[float], period: int = 14) -> float:
    changes = [right - left for left, right in zip(closes, closes[1:], strict=False)]
    gains = [max(change, 0) for change in changes[-period:]]
    losses = [abs(min(change, 0)) for change in changes[-period:]]
    average_loss = fmean(losses)
    if average_loss == 0:
        return 100.0
    return 100 - (100 / (1 + (fmean(gains) / average_loss)))


def _atr(snapshot: MarketSnapshot, period: int = 14) -> Decimal:
    candles = snapshot.candles[-(period + 1) :]
    ranges = [
        max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )
        for previous, current in zip(candles, candles[1:], strict=False)
    ]
    return sum(ranges, Decimal("0")) / Decimal(len(ranges))


def propose(snapshot: MarketSnapshot) -> TradeDecision:
    if len(snapshot.candles) < 50:
        return TradeDecision(
            "HOLD", 0, Decimal("0"), snapshot.mid_price, None, None, ["insufficient candles"], {}
        )
    closes = [float(candle.close) for candle in snapshot.candles]
    fast, slow, rsi, atr = (
        _ema(closes[-21:], 9),
        _ema(closes[-50:], 21),
        _rsi(closes),
        _atr(snapshot),
    )
    action: Action = "HOLD"
    reasons = [f"EMA9={fast:.4f}", f"EMA21={slow:.4f}", f"RSI14={rsi:.1f}", f"ATR14={atr}"]
    if fast > slow and 52 <= rsi <= 68:
        action = "BUY"
        reasons.append("trend and momentum aligned for long entry")
    elif fast < slow and rsi >= 70:
        action = "SELL"
        reasons.append("weak trend with overbought momentum; exit signal")
    else:
        reasons.append("no high-conviction setup")
    return TradeDecision(
        action=action,
        confidence=0.7 if action != "HOLD" else 0.2,
        quantity=Decimal("0"),
        entry_price=snapshot.best_ask if action == "BUY" else snapshot.best_bid,
        stop_loss=None,
        take_profit=None,
        reasons=reasons,
        signal_values={
            "ema_fast": f"{fast:.8f}",
            "ema_slow": f"{slow:.8f}",
            "rsi": f"{rsi:.4f}",
            "atr": str(atr),
        },
    )
