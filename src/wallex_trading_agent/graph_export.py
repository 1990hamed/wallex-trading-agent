"""Export the LangGraph workflow as a Mermaid diagram for project documentation."""

from pathlib import Path

from wallex_trading_agent.agent import TradingAgent
from wallex_trading_agent.config import Settings


def main() -> None:
    """Write the current compiled agent graph to ``docs/agent_graph.mmd``."""
    settings = Settings()
    graph = TradingAgent(settings).graph.get_graph()
    output = Path("docs/agent_graph.mmd")
    output.parent.mkdir(parents=True, exist_ok=True)
    mermaid = graph.draw_mermaid()
    notes = (
        "\n%% Indicators: EMA9, EMA21, RSI14, ATR14, ADX14\n"
        "%% execute_or_shadow also enforces TRADING_END_TIME liquidation.\n"
    )
    output.write_text(mermaid + notes, encoding="utf-8")
    print(f"Agent graph exported to {output}")

