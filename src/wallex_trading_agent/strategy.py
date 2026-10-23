from __future__ import annotations

from decimal import Decimal
from statistics import fmean

from wallex_trading_agent.models import Action, MarketSnapshot, TradeDecision


def _ema(values: list[float], period: int) -> float:
    """Calculate an exponential moving average for a close-price series."""
    alpha = 2 / (period + 1)
    value = values[0]
    for close in values[1:]:
        value = (close * alpha) + (value * (1 - alpha))
    return value


def _rsi(closes: list[float], period: int = 14) -> float:
    """Calculate the bounded relative-strength index."""
    changes = [right - left for left, right in zip(closes, closes[1:], strict=False)]
    gains = [max(change, 0) for change in changes[-period:]]
    losses = [abs(min(change, 0)) for change in changes[-period:]]
    average_loss = fmean(losses)
    if average_loss == 0:
        return 100.0
    return 100 - (100 / (1 + (fmean(gains) / average_loss)))


def _atr(snapshot: MarketSnapshot, period: int = 14) -> Decimal:
    """Calculate average true range from the latest candles."""
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


def _adx(snapshot: MarketSnapshot, period: int = 14) -> float:
    """Measure trend strength on a 0-100 scale using directional movement."""
    candles = snapshot.candles[-(period + 1) :]
    if len(candles) < period + 1:
        return 0.0
    true_ranges: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for previous, current in zip(candles, candles[1:], strict=False):
        up_move = float(current.high - previous.high)
        down_move = float(previous.low - current.low)
        plus_dm.append(max(up_move, 0.0) if up_move > down_move else 0.0)
        minus_dm.append(max(down_move, 0.0) if down_move > up_move else 0.0)
        true_ranges.append(
            float(
                max(
                    current.high - current.low,
                    abs(current.high - previous.close),
                    abs(current.low - previous.close),
                )
            )
        )
    average_tr = fmean(true_ranges)
    if average_tr == 0:
        return 0.0
    plus_di = 100 * fmean(plus_dm) / average_tr
    minus_di = 100 * fmean(minus_dm) / average_tr
    denominator = plus_di + minus_di
    return 100 * abs(plus_di - minus_di) / denominator if denominator else 0.0


def propose(snapshot: MarketSnapshot) -> TradeDecision:
    """Generate a deterministic EMA/RSI/ATR Spot decision."""
    if len(snapshot.candles) < 50:
        return TradeDecision(
            "HOLD", 0, Decimal("0"), snapshot.mid_price, None, None, ["دادهٔ کندلی کافی نیست"], {}
        )
    closes = [float(candle.close) for candle in snapshot.candles]
    fast, slow, rsi, atr, adx = (
        _ema(closes[-21:], 9),
        _ema(closes[-50:], 21),
        _rsi(closes),
        _atr(snapshot),
        _adx(snapshot),
    )
    action: Action = "HOLD"
    reasons = [
        f"EMA9={fast:.4f}",
        f"EMA21={slow:.4f}",
        f"RSI14={rsi:.1f}",
        f"ATR14={atr}",
        f"ADX14={adx:.1f}",
    ]
    if fast > slow and 52 <= rsi <= 68 and adx >= 20:
        action = "BUY"
        reasons.append("روند و مومنتوم برای ورود خرید هم‌سو هستند")
    elif fast < slow and rsi >= 70 and adx >= 20:
        action = "SELL"
        reasons.append("روند ضعیف و مومنتوم بیش‌خرید است؛ سیگنال خروج")
    else:
        reasons.append("فرصت معاملاتی با اطمینان بالا دیده نشد")
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
            "adx": f"{adx:.4f}",
        },
    )
