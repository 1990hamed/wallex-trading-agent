from __future__ import annotations

import json
import logging
import sys

from wallex_trading_agent.agent import TradingAgent
from wallex_trading_agent.config import Settings
from wallex_trading_agent.models import DecisionLog


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
        mcp_tools=state["mcp_tools"],
        ai_review=state["ai_review"],
        execution=state["execution"],
    )
    settings.decision_log_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.decision_log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry.to_dict(), default=str, ensure_ascii=False) + "\n")
    # Windows consoles may still use cp1252; escaped JSON keeps the CLI reliable.
    action_names = {"BUY": "خرید", "SELL": "فروش", "HOLD": "نگهداری"}
    print("=" * 60)
    print("گزارش اجرای عامل معاملاتی والکس")
    print(f"نماد: {entry.symbol}")
    print(f"حالت اجرا: {'سایه (بدون سفارش واقعی)' if entry.mode == 'shadow' else 'واقعی'}")
    print(f"تصمیم: {action_names.get(entry.decision.action, entry.decision.action)}")
    print(f"قیمت ورود: {entry.decision.entry_price}")
    print(f"اعتماد: {entry.decision.confidence:.0%}")
    print("دلایل:")
    for reason in entry.decision.reasons:
        print(f"  - {reason}")
    ai_status = {
        "confirmed": "تأیید شد",
        "vetoed: low confidence or HOLD": "رد شد: اطمینان کم یا HOLD",
        "vetoed: conflicting action": "رد شد: اقدام متناقض",
        "failed": "خطا در بررسی",
        "skipped": "رد شد: کلید مدل تنظیم نشده",
    }.get(str(entry.ai_review.get("status")), str(entry.ai_review.get("status", "نامشخص")))
    print(f"بررسی BoxAPI: {ai_status}")
    print(f"کنترل ریسک: {entry.risk_reason}")
    execution_status = {
        "skipped": "رد شد",
        "submitted": "ارسال شد",
    }.get(str(entry.execution.get("status")), str(entry.execution.get("status", "نامشخص")))
    print(f"نتیجه اجرا: {execution_status}")
    print("لاگ کامل: " + str(settings.decision_log_path))
    print("=" * 60)
