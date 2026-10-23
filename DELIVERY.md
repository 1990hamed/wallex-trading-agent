# Wallex Trading Agent — Submission Documentation

This document describes the exact version of the algorithm used during the trading challenge.

## Architecture

Each execution cycle is orchestrated by LangGraph in `runner.py`:

1. `collect_market`: Retrieves bid/ask prices and candlesticks from Wallex REST, along with the list of available Wallex MCP tools.
2. `propose_trade`: Generates deterministic signals using EMA, RSI, ATR, and ADX.
3. `ai_review`: Performs a structured review through BoxAPI (OpenAI-compatible). The model can only approve the signal or return `HOLD`.
4. `risk_check`: Validates account balances, position sizing, per-trade risk, and the maximum allocation limit.
5. `execute_or_shadow`: Records the recommendation in Shadow mode or submits a Spot order with an idempotent identifier in Live mode.
6. Records one JSONL entry per cycle in `data/decision_log.jsonl`.

Backtests are recorded in `data/backtest_log.jsonl`, and all timestamps use the `Asia/Tehran` time zone.

## AI and Wallex Tools

The MCP connection to `https://api.wallex.ir/mcp` is used to discover available tools, and the names of discovered tools are stored in the logs. The executable and auditable trading path uses the official Wallex REST API.

BoxAPI is called through an OpenAI-compatible endpoint. Its response is validated against a structured model, and any error results in a safe fallback to `HOLD`.

## Buy and Sell Rules

- **BUY** is executed only when the deterministic signal has been approved by the AI review.
- **SELL** is permitted only for existing Spot holdings; short selling is not supported.
- Weak signals, AI disagreements, insufficient balances, or missing API keys result in a safe `HOLD` or rejection.
- For BUY orders, stop-loss and take-profit levels are calculated using ATR and recorded after the entry order is filled.
- Both BUY and SELL signals are generated only when the trend strength satisfies `ADX14 >= 20`.
- The Spot stop-loss uses a `STOP_LIMIT` order, while the take-profit uses a Limit sell order.

## Capital and Risk Management

- Initial capital: `5,000,000 TMN`.
- Per-trade risk and the maximum allocation limit are read from `.env`.
- Trading fees are included in performance reports.
- Orders use a persistent `client_id` to prevent duplicate orders during repeated executions.
- At the end of the challenge, settlement is rejected if any coin balance remains open. Returns are calculated solely from TMN cash and realized profits.

## Reproducibility and Evaluation

```powershell
uv sync --all-groups
uv run wallex-trading-agent       # One cycle, Shadow mode by default
uv run wallex-backtest            # Historical evaluation of the configured symbol
uv run wallex-settle              # Final report only when the coin balance is zero
uv run wallex-healthcheck         # Read-only connection and market-rule checks
uv run wallex-graph               # Generate a Mermaid diagram of the Agent graph
uv run pytest -q
uv run ruff check .
```

All configuration is read from `.env`, and the CLI does not use `argparse`.

The replayable decision log in JSONL includes timestamps, symbols, actions, signals, explanations in Persian, AI review results, risk checks, execution outcomes, and actual fills. The complete schema is documented in `docs/DECISION_LOG_SCHEMA.md`.

## Submission Safety Status

The default mode is `shadow`. Orders are submitted only when both `TRADING_MODE=live` and `ENABLE_LIVE_TRADING=true` are enabled simultaneously. API keys are stored in `.env` and are not committed to version control.

The end of the trading session can be configured using `TRADING_END_TIME` and `LIQUIDATION_BUFFER_MINUTES`. At the specified end time, the Agent stops initiating new buys and attempts to sell the existing Spot holdings.