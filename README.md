# Wallex Trading Agent

An auditable, safety-first trading agent for the Wallex hackathon. It uses a LangGraph workflow, discovers Wallex MCP tools at `https://api.wallex.ir/mcp`, and uses the Wallex REST API for verifiable market data and order submission.

## Safety model

- The default is `TRADING_MODE=shadow`: it produces and logs proposed orders, but submits nothing.
- Live order submission requires **both** `TRADING_MODE=live` and `ENABLE_LIVE_TRADING=true`.
- The LLM can veto a trade but cannot override the deterministic risk checks.
- BoxAPI is preferred when `BOXAPI_API_KEY` is configured; it is passed through the OpenAI-compatible ChatOpenAI client using `BOXAPI_API_URL_BASE`.
- Every cycle writes a JSONL decision record: indicators, AI review, risk outcome, and execution result.
- Performance accounting uses the 5,000,000 TMN initial capital, FIFO realized PnL, quote-currency fees, and excludes open coin inventory from the return percentage.
- API keys stay in `.env`, which is ignored by Git.

This is a hackathon prototype, not investment advice. Run shadow testing and review decision logs before any live trading.

## Architecture

```text
Wallex REST + configured MCP server
              |
        collect_market
              |
        propose_trade (EMA, RSI, ATR)
              |
        ai_review (OpenAI structured decision / veto)
              |
        risk_check (size, stop-loss, allocation caps)
              |
        execute_or_shadow
              |
        JSONL decision log
```

The MCP connection is used to discover the Wallex tools exposed to the agent and makes that inventory visible to the AI review. The minimal REST client provides the stable market-data and explicit order-submission path. This separation makes the order path easy for judges to inspect.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```powershell
Copy-Item .env.example .env
uv sync --all-groups
uv run wallex-trading-agent
```

There are no command-line flags and no `argparse`; configuration is exclusively environment-based. Change `.env` to select a permitted `SYMBOL`, resolution, or risk limits.

The supplied `.env` is already excluded from Git. Do not paste API keys into issues, logs, commits, or demos.

## Quality checks

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Run these before every commit. The initial GitHub push is intentionally not performed by the agent until the repository remote and target account are confirmed.

The repository also includes a GitHub Actions workflow that repeats these checks on every push and pull request.

## Going live

1. Review `data/decision_log.jsonl` after shadow cycles.
2. Verify the challenge's approved market, available balance, minimum quantity, and order tick/step requirements.
3. Set both explicit live gates in your local `.env`.
4. Start with a deliberately small risk cap. The agent submits only a limit order and preserves its unique `client_id` in the Wallex response.

The runner executes one deterministic cycle per invocation. Use a supervised scheduler only after shadow testing, rather than an unmonitored infinite loop.
