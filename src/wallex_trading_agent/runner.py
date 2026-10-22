from __future__ import annotations

import json
import logging

from wallex_trading_agent.agent import TradingAgent
from wallex_trading_agent.config import Settings
from wallex_trading_agent.models import DecisionLog


def main() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.log_level)
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
    print(json.dumps(entry.to_dict(), default=str, ensure_ascii=True, indent=2))
