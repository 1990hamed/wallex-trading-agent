from __future__ import annotations

import json

from wallex_trading_agent.config import Settings
from wallex_trading_agent.performance import fills_from_decision_records, settle_challenge


def main() -> None:
    settings = Settings()
    path = settings.decision_log_path
    records = (
        [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if path.exists()
        else []
    )
    report = settle_challenge(fills_from_decision_records(records), settings.initial_capital_tmn)
    print("Challenge settlement")
    print(f"Initial capital (TMN): {report.initial_capital}")
    print(f"Final cash (TMN): {report.final_cash}")
    print(f"Realized PnL (TMN): {report.realized_pnl}")
    print(f"Fees (TMN): {report.total_fees}")
    print(f"Net return: {report.return_percent}%")

