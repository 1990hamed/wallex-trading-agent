from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from wallex_trading_agent.backtest import run_backtest
from wallex_trading_agent.config import Settings
from wallex_trading_agent.wallex import WallexClient

TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def main() -> None:
    settings = Settings()
    api_key = settings.wallex_api_key.get_secret_value() if settings.wallex_api_key else None
    candles = WallexClient(api_key).historical_candles(
        settings.symbol, settings.candle_resolution, settings.candle_count
    )
    result = run_backtest(
        candles,
        symbol=settings.symbol,
        initial_capital=settings.initial_capital_tmn,
        max_position_fraction=Decimal(str(settings.max_position_fraction)),
    )
    settings.backtest_log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(TEHRAN_TZ).isoformat(),
        "symbol": settings.symbol,
        "candle_count": len(candles),
        "trade_count": result.trade_count,
        "report": result.report.to_dict(),
    }
    with settings.backtest_log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Symbol: {settings.symbol}")
    print(f"Candles: {len(candles)}")
    print(f"Fills: {result.trade_count}")
    print(f"Realized PnL (TMN): {result.report.realized_pnl}")
    print(f"Return: {result.report.return_percent}%")
    print(f"Open quantity (excluded): {result.report.open_quantity}")
    print(f"Backtest log: {settings.backtest_log_path}")
