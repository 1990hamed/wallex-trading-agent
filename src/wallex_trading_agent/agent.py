from __future__ import annotations

from decimal import Decimal
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from wallex_trading_agent.config import Settings
from wallex_trading_agent.mcp import McpToolCatalog
from wallex_trading_agent.models import MarketSnapshot, TradeDecision
from wallex_trading_agent.strategy import propose
from wallex_trading_agent.wallex import WallexClient


class AIReview(BaseModel):
    action: str = Field(description="BUY, SELL, or HOLD")
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(max_length=500)
    risk_flag: str = Field(max_length=300)


class AgentState(TypedDict, total=False):
    snapshot: MarketSnapshot
    deterministic_decision: TradeDecision
    decision: TradeDecision
    mcp_tools: list[str]
    ai_review: dict[str, Any]
    risk_approved: bool
    risk_reason: str
    execution: dict[str, object]


class TradingAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        api_key = settings.wallex_api_key.get_secret_value() if settings.wallex_api_key else None
        self.wallex = WallexClient(api_key)
        self.mcp_catalog = McpToolCatalog(settings)
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("collect_market", self._collect_market)
        graph.add_node("propose_trade", self._propose_trade)
        graph.add_node("ai_review", self._ai_review)
        graph.add_node("risk_check", self._risk_check)
        graph.add_node("execute_or_shadow", self._execute_or_shadow)
        graph.add_edge(START, "collect_market")
        graph.add_edge("collect_market", "propose_trade")
        graph.add_edge("propose_trade", "ai_review")
        graph.add_edge("ai_review", "risk_check")
        graph.add_edge("risk_check", "execute_or_shadow")
        graph.add_edge("execute_or_shadow", END)
        return graph.compile()

    def run_once(self) -> AgentState:
        return self.graph.invoke({})

    def _collect_market(self, _: AgentState) -> AgentState:
        snapshot = self.wallex.market_snapshot(
            self.settings.symbol, self.settings.candle_resolution, self.settings.candle_count
        )
        return {"snapshot": snapshot, "mcp_tools": self.mcp_catalog.names}

    def _propose_trade(self, state: AgentState) -> AgentState:
        return {"deterministic_decision": propose(state["snapshot"])}

    def _ai_review(self, state: AgentState) -> AgentState:
        candidate = state["deterministic_decision"]
        if not self.settings.model_api_key:
            return {
                "decision": candidate,
                "ai_review": {"status": "skipped", "reason": "کلید مدل تنظیم نشده است"},
            }
        try:
            from langchain_openai import ChatOpenAI

            model_kwargs = {
                "model": self.settings.ai_model,
                "temperature": 0,
                "api_key": self.settings.model_api_key.get_secret_value(),
            }
            if self.settings.model_base_url:
                model_kwargs["base_url"] = self.settings.model_base_url
            review_model = ChatOpenAI(**model_kwargs).with_structured_output(AIReview)
            review = review_model.invoke(
                [
                    (
                        "system",
                        "تو یک ارزیاب محافظه‌کار معاملات اسپات رمزارز هستی. قیمت جعل نکن. "
                        "فقط وقتی شواهد کمی منسجم است BUY یا SELL را تأیید کن. "
                        "وقتی شواهد ضعیف یا نامطمئن است HOLD برگردان. "
                        "rationale و risk_flag را فارسی بنویس.",
                    ),
                    (
                        "human",
                        f"نماد: {state['snapshot'].symbol}\n"
                        f"پیشنهاد اولیه: {candidate.action}\nسیگنال‌ها: {candidate.signal_values}\n"
                        f"دلایل اولیه: {candidate.reasons}\n"
                        f"ابزارهای MCP والکس: {state['mcp_tools']}",
                    ),
                ]
            )
            review_data = review.model_dump()
            # The AI may confirm or veto a candidate, never override risk logic.
            if review.action not in {candidate.action, "HOLD"}:
                review_data["status"] = "vetoed: conflicting action"
                return {
                    "decision": self._hold(candidate, "هوش مصنوعی اقدام متناقض برگرداند"),
                    "ai_review": review_data,
                }
            if review.action == "HOLD" or review.confidence < 0.60:
                review_data["status"] = "vetoed: low confidence or HOLD"
                return {
                    "decision": self._hold(candidate, f"رد توسط BoxAPI: {review.rationale}"),
                    "ai_review": review_data,
                }
            review_data["status"] = "confirmed"
            return {"decision": candidate, "ai_review": review_data}
        except Exception as exc:
            return {
                "decision": self._hold(candidate, "بررسی BoxAPI در دسترس نبود؛ توقف امن"),
                "ai_review": {"status": "failed", "reason": type(exc).__name__},
            }

    @staticmethod
    def _hold(candidate: TradeDecision, reason: str) -> TradeDecision:
        return TradeDecision(
            action="HOLD",
            confidence=0,
            quantity=Decimal("0"),
            entry_price=candidate.entry_price,
            stop_loss=None,
            take_profit=None,
            reasons=[*candidate.reasons, reason],
            signal_values=candidate.signal_values,
        )

    def _risk_check(self, state: AgentState) -> AgentState:
        decision = state["decision"]
        if decision.action == "HOLD":
            return {"risk_approved": False, "risk_reason": "سیگنال تأییدشده‌ای وجود ندارد"}
        if not self.settings.wallex_api_key:
            return {"risk_approved": False, "risk_reason": "کلید WALLEX_API_KEY تنظیم نشده است"}
        balances = self.wallex.balances()
        base, quote = self._split_symbol(self.settings.symbol)
        if decision.action == "BUY":
            available = Decimal(str(balances.get(quote, {}).get("value", 0)))
            return self._size_buy(state, available)
        available = Decimal(str(balances.get(base, {}).get("value", 0)))
        if available <= 0:
            return {"risk_approved": False, "risk_reason": f"موجودی {base} برای فروش کافی نیست"}
        quantity = available * Decimal(str(self.settings.max_position_fraction))
        return {
            "decision": self._with_quantity(decision, quantity),
            "risk_approved": True,
            "risk_reason": "حجم فروش در سقف مجاز محدود شد",
        }

    def _size_buy(self, state: AgentState, available_quote: Decimal) -> AgentState:
        decision = state["decision"]
        if available_quote <= 0:
            return {"risk_approved": False, "risk_reason": "موجودی ارز مظنه برای خرید وجود ندارد"}
        atr = Decimal(decision.signal_values["atr"])
        stop_distance = atr * Decimal(str(self.settings.stop_loss_atr))
        if stop_distance <= 0:
            return {"risk_approved": False, "risk_reason": "ATR برای محاسبه حد ضرر معتبر نیست"}
        risk_quantity = (
            available_quote * Decimal(str(self.settings.risk_per_trade))
        ) / stop_distance
        position_quantity = (
            available_quote * Decimal(str(self.settings.max_position_fraction))
        ) / decision.entry_price
        quantity = min(risk_quantity, position_quantity)
        stop_loss = decision.entry_price - stop_distance
        take_profit = decision.entry_price + (atr * Decimal(str(self.settings.take_profit_atr)))
        sized = TradeDecision(
            **{
                **decision.__dict__,
                "quantity": quantity,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            }
        )
        return {
            "decision": sized,
            "risk_approved": True,
            "risk_reason": "حجم موقعیت زیر سقف ریسک و تخصیص سرمایه است",
        }

    @staticmethod
    def _with_quantity(decision: TradeDecision, quantity: Decimal) -> TradeDecision:
        return TradeDecision(**{**decision.__dict__, "quantity": quantity})

    @staticmethod
    def _split_symbol(symbol: str) -> tuple[str, str]:
        for quote in ("USDT", "TMN", "BTC", "ETH"):
            if symbol.endswith(quote):
                return symbol[: -len(quote)], quote
        raise ValueError(f"Cannot infer base/quote assets from {symbol}")

    def _execute_or_shadow(self, state: AgentState) -> AgentState:
        decision = state["decision"]
        if not state["risk_approved"]:
            return {"execution": {"status": "رد شد", "reason": state["risk_reason"]}}
        if not self.settings.live_execution_allowed:
            return {
                "execution": {
                    "status": "سایه",
                    "reason": (
                        "برای سفارش، TRADING_MODE=live و "
                        "ENABLE_LIVE_TRADING=true را تنظیم کنید"
                    ),
                    "side": decision.action,
                    "price": str(decision.entry_price),
                    "quantity": str(decision.quantity),
                }
            }
        result = self.wallex.create_limit_order(
            symbol=self.settings.symbol,
            side=decision.action,
            price=decision.entry_price,
            quantity=decision.quantity,
        )
        return {"execution": {"status": "ارسال شد", "result": result.get("result", result)}}
