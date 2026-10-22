# Decision log schema

هر خط `data/decision_log.jsonl` یک JSON مستقل است. این فایل runtime است و به‌دلیل وجود داده حساب در Git commit نمی‌شود.

```json
{
  "timestamp": "UTC ISO-8601",
  "mode": "shadow|live",
  "symbol": "BTCTMN",
  "decision": {
    "action": "BUY|SELL|HOLD",
    "confidence": 0.0,
    "quantity": "0",
    "entry_price": "0",
    "stop_loss": "0|null",
    "take_profit": "0|null",
    "reasons": ["دلیل سیگنال و تصمیم"],
    "signal_values": {"ema_fast": "...", "ema_slow": "...", "rsi": "...", "atr": "..."}
  },
  "risk_approved": false,
  "risk_reason": "...",
  "mcp_tools": ["tool name"],
  "ai_review": {"status": "confirmed|vetoed|failed|skipped", "rationale": "..."},
  "execution": {"status": "سایه|ارسال شد|رد شد", "result": {}, "protective_orders": {} }
}
```

این ساختار دلیل هر معامله، سیگنال مشاهده‌شده، نظر AI و نتیجه واقعی سفارش را برای داوری فنی نگه می‌دارد.
