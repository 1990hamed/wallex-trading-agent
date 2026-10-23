# Decision Log Schema

Each line in `data/decision_log.jsonl` is an independent JSON object. This is a runtime file and is not committed to Git because it contains account-related data.

```json
{
  "timestamp": "Asia/Tehran ISO-8601",
  "mode": "shadow|live",
  "symbol": "BTCTMN",
  "decision": {
    "action": "BUY|SELL|HOLD",
    "confidence": 0.0,
    "quantity": "0",
    "entry_price": "0",
    "stop_loss": "0|null",
    "take_profit": "0|null",
    "reasons": ["Signal and decision rationale"],
    "signal_values": {
      "ema_fast": "...",
      "ema_slow": "...",
      "rsi": "...",
      "atr": "...",
      "adx": "..."
    }
  },
  "risk_approved": false,
  "risk_reason": "...",
  "mcp_tools": ["tool name"],
  "ai_review": {
    "status": "confirmed|vetoed|failed|skipped",
    "rationale": "..."
  },
  "execution": {
    "status": "shadow|submitted|rejected|liquidation_submitted|settled",
    "result": {},
    "protective_orders": {}
  }
}
```

This structure preserves the rationale behind each trade, the observed signals, the AI's assessment, and the actual order execution results for technical evaluation.

Backtest records are stored in `data/backtest_log.jsonl` and contain aggregate fields such as `buy_count`, `sell_count`, `completed_trade_count`, `realized_pnl`, `final_cash`, `total_fees`, `return_percent`, and `open_quantity`.