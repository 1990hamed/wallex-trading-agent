# Wallex Spot Trading Strategy

## Overview

This project is an automated trading engine for the **Wallex Spot market**. The agent makes buy, sell, or hold decisions using market data, technical indicators, BoxAPI review, and deterministic risk management rules.

The current strategy is intentionally conservative: when there is insufficient evidence, it issues a `HOLD` decision. The goal is not to trade without logic, but to generate repeatable, realized returns while controlling drawdowns.

## Decision-Making Workflow

```text
Wallex REST + Wallex MCP
          │
          ▼
Fetch order book and candlesticks
          │
          ▼
Calculate EMA9, EMA21, RSI14, ATR14, and ADX14
          │
          ▼
Generate initial strategy recommendation
          │
          ▼
Conservative review with BoxAPI
          │
          ▼
Balance checks and risk management
          │
          ▼
Shadow execution or Spot order placement
          │
          ▼
Log rationale, fills, and results to JSONL
```

## Input Data

For the symbol configured in `.env`, the agent retrieves the following:

- Best bid and ask prices from the order book;
- Historical candlesticks using the configured resolution;
- Account balances to determine whether buying or selling is possible;
- Wallex MCP tools to access and inspect the exchange's official capabilities.

The symbol is read from `SYMBOL` and must represent an eligible Spot market. The recommended current configuration is:

```env
SYMBOL=BTCTMN
CANDLE_RESOLUTION=60
CANDLE_COUNT=120
```

## Technical Indicators

### EMA

Short-term and medium-term exponential moving averages are used to identify the market trend:

- EMA9: Short-term trend;
- EMA21: Medium-term trend.

### RSI14

RSI measures price momentum and identifies overbought or oversold conditions. A low RSI alone is not a buy signal; it must be evaluated alongside the trend and other indicators.

### ATR14

ATR estimates market volatility and is used to determine trade size, stop-loss levels, and take-profit levels. It does not determine market direction.

### ADX14

ADX measures trend strength without indicating its direction. The condition `ADX14 >= 20` helps avoid entering trades in weak or sideways markets.

## Trade Recommendation Rules

### Spot Buy

A buy recommendation is generated when the following conditions are met:

```text
EMA9 > EMA21
52 <= RSI14 <= 68
ADX14 >= 20
```

This indicates a positive short-term trend, with momentum that has not yet entered an excessively overbought zone.

### Spot Sell

A sell/exit recommendation is generated when the following conditions are met:

```text
EMA9 < EMA21
RSI14 >= 70
ADX14 >= 20
```

Selling is permitted only when the relevant asset is already held. The system does not support short selling or selling assets that are not available in the account.

### Hold

In all other situations, the system issues a `HOLD` decision. This includes sideways markets, unclear trends, unsuitable RSI values, and insufficient data.

## Role of BoxAPI

BoxAPI reviews the initial recommendation and returns an explainable rationale and a risk flag. The model is not allowed to override deterministic risk management rules.

A recommendation is approved only when:

- BoxAPI confirms the same action;
- Confidence is at least `0.60`;
- The model's reasoning does not contradict the quantitative data.

In the event of disagreement, low confidence, a model error, or a `HOLD` response, the system defaults to `HOLD` as a safety measure.

## Risk Management

Default configuration:

```env
RISK_PER_TRADE=0.005
MAX_POSITION_FRACTION=0.10
STOP_LOSS_ATR=1.5
TAKE_PROFIT_ATR=2.5
MAX_DAILY_LOSS_FRACTION=0.02
```

For a buy order:

```text
stop_distance = ATR14 × STOP_LOSS_ATR

risk_quantity =
    quote_currency_balance × RISK_PER_TRADE / stop_distance

position_quantity =
    quote_currency_balance × MAX_POSITION_FRACTION / entry_price

quantity = minimum of the two quantities above
```

Suggested stop-loss and take-profit levels:

```text
stop_loss = entry_price - (ATR14 × STOP_LOSS_ATR)

take_profit = entry_price + (ATR14 × TAKE_PROFIT_ATR)
```

Selling is limited to a specified fraction of the available asset balance. If no balance is available, the sell order is rejected.

## Capital and Performance Calculation

Initial capital for the trading challenge:

```text
initial_capital = 5,000,000 TMN
```

The performance module processes trades using the FIFO (First In, First Out) method and reports the following:

- Realized PnL;
- Total trading fees;
- Final cash balance;
- Percentage return relative to initial capital;
- Remaining open coin position.

Return formula:

```text
return (%) = ((final_cash - initial_capital) / initial_capital) × 100
```

Unrealized holdings are excluded from realized returns and reported separately. To finalize the trading challenge, all open positions must be closed and the resulting profit or loss must be realized in TMN.

## Execution Modes

The default execution mode is Shadow:

```env
TRADING_MODE=shadow
ENABLE_LIVE_TRADING=false
```

In this mode, market data is retrieved and trading decisions are generated, but no real orders are placed.

Live execution is permitted only when both of the following settings are enabled:

```env
TRADING_MODE=live
ENABLE_LIVE_TRADING=true
```

## Logging and Reproducibility

Each cycle is recorded in `data/decision_log.jsonl` and includes:

- Symbol and timestamp;
- EMA, RSI, ATR, and ADX values;
- Initial action and confidence;
- Strategy and BoxAPI explanations in Persian;
- Discovered MCP tools;
- Risk check results;
- Order responses and fills, when live execution is enabled.

The CLI displays its summary in English, while decision explanations are stored in Persian in the log.

Timestamps are recorded using the `Asia/Tehran` time zone, and backtest logs are stored separately in `data/backtest_log.jsonl`.

## User-Defined End Time

When `TRADING_END_TIME` is configured, new buy orders are disabled during the final buffer period. At the specified end time, open orders are canceled and the Spot holdings are sold for settlement in TMN.

Successful liquidation depends on market liquidity, API availability, and the order reaching the `FILLED` status.

## Limitations and Requirements for Final Evaluation

- Current thresholds must be evaluated through backtesting on real Wallex market data.
- Accurate final performance calculations require actual trade fills and all applicable fees to be retrieved from the trading challenge account.
- Before enabling live trading, minimum quantity, tick size, precision, and market liquidity must be verified.
- Before the challenge ends, all open positions must be closed so that performance can be measured using realized returns denominated in TMN.
- Increasing the number of trades is not a goal in itself. The primary metrics are net returns, loss control, and execution reliability.

## Running the Agent

```powershell
uv run wallex-trading-agent
```

This command executes one cycle, records the decision, and stops in Shadow mode.