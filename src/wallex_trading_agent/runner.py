from __future__ import annotations

import json
import logging
import sys

from wallex_trading_agent.agent import TradingAgent
from wallex_trading_agent.config import Settings
from wallex_trading_agent.models import DecisionLog
from wallex_trading_agent.performance import (
    calculate_realized_performance,
    fills_from_decision_records,
)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    settings = Settings()
    logging.basicConfig(level=settings.log_level)
    for noisy_logger in ("httpx", "httpcore", "httpx2", "mcp.client.streamable_http"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    agent = TradingAgent(settings)
    state = agent.run_once()
    entry = DecisionLog.create(
        mode=settings.trading_mode,
        symbol=settings.symbol,
        decision=state["decision"],
        risk_approved=state["risk_approved"],
        risk_reason=state["risk_reason"],
        ai_review=state["ai_review"],
        execution=state["execution"],
    )
    settings.decision_log_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.decision_log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry.to_dict(), default=str, ensure_ascii=False) + "\n")
    records = [
        json.loads(line)
        for line in settings.decision_log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    performance = calculate_realized_performance(
        fills_from_decision_records(records), settings.initial_capital_tmn
    )
    # Windows consoles may still use cp1252; escaped JSON keeps the CLI reliable.
    action_names = {"BUY": "BUY", "SELL": "SELL", "HOLD": "HOLD"}
    print("=" * 60)
    print("Wallex Trading Agent Run")
    print(f"Symbol: {entry.symbol}")
    print(f"Mode: {'shadow (no live order)' if entry.mode == 'shadow' else 'live'}")
    print(f"Decision: {action_names.get(entry.decision.action, entry.decision.action)}")
    print(f"Entry price: {entry.decision.entry_price}")
    print(f"Confidence: {entry.decision.confidence:.0%}")
    print("Signals:")
    for name, value in entry.decision.signal_values.items():
        print(f"  - {name}: {value}")
    ai_status = {
        "confirmed": "confirmed",
        "vetoed: low confidence or HOLD": "vetoed: low confidence or HOLD",
        "vetoed: conflicting action": "vetoed: conflicting action",
        "failed": "review failed",
        "skipped": "skipped: model key is not configured",
    }.get(str(entry.ai_review.get("status")), str(entry.ai_review.get("status", "نامشخص")))
    print(f"BoxAPI review: {ai_status}")
    risk_reason = {
        "سیگنال تأییدشده‌ای وجود ندارد": "no approved trading signal",
        "کلید WALLEX_API_KEY تنظیم نشده است": "WALLEX_API_KEY is not configured",
        "موجودی ارز مظنه برای خرید وجود ندارد": "no quote balance available",
        "حجم فروش در سقف مجاز محدود شد": "sell size capped",
        "حجم موقعیت زیر سقف ریسک و تخصیص سرمایه است": "position is below risk and allocation caps",
    }.get(entry.risk_reason, "risk check completed")
    print(f"Risk control: {risk_reason}")
    execution_status = {
        "رد شد": "rejected",
        "سایه": "shadow",
        "ارسال شد": "submitted",
        "skipped": "rejected",
        "submitted": "submitted",
    }.get(str(entry.execution.get("status")), str(entry.execution.get("status", "unknown")))
    print(f"Execution result: {execution_status}")
    print(f"Realized PnL (TMN): {performance.realized_pnl}")
    print(f"Net return: {performance.return_percent}%")
    print(f"Open coin quantity (excluded from return): {performance.open_quantity}")
    print("Full log: " + str(settings.decision_log_path))
    print("=" * 60)
