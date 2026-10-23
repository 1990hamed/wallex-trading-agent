"""Configuration comes only from environment variables and .env; no CLI parsing."""

from decimal import Decimal
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings and explicit live-trading safety gates."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr | None = Field(None, description="Optional OpenAI API key")
    boxapi_api_key: SecretStr | None = Field(None, description="BoxAPI key")
    boxapi_api_url_base: str = Field("https://ai.boxapi.ir/ai/v1", description="BoxAPI base URL")
    wallex_api_key: SecretStr | None = Field(None, description="Wallex API key")
    mcp_server_url: str = Field("https://api.wallex.ir/mcp", description="Wallex MCP URL")
    ai_model: str = Field("gpt-5.6-mini", description="Model name")
    log_level: str = Field("INFO", description="Python logging level")
    trading_mode: str = Field("shadow", description="shadow or live execution mode")
    enable_live_trading: bool = Field(False, description="Second live-order safety gate")
    symbol: str = Field("BTCTMN", description="Spot market symbol")
    candle_resolution: str = Field("60", description="Candle interval in minutes")
    candle_count: int = Field(default=120, ge=50, le=1000, description="Historical candle count")
    poll_interval_seconds: int = Field(default=300, ge=30, description="Cycle interval in seconds")
    risk_per_trade: float = Field(
        default=0.005, gt=0, le=0.02, description="Risk fraction per trade"
    )
    max_daily_loss_fraction: float = Field(default=0.02, gt=0, le=0.1, description="Daily loss cap")
    initial_capital_tmn: Decimal = Field(Decimal("5000000"), description="Challenge capital in TMN")
    max_position_fraction: float = Field(
        default=0.10, gt=0, le=0.25, description="Position allocation cap"
    )
    stop_loss_atr: float = Field(default=1.5, gt=0, le=5, description="Stop distance in ATR")
    take_profit_atr: float = Field(default=2.5, gt=0, le=8, description="Target distance in ATR")
    decision_log_path: Path = Field(Path("data/decision_log.jsonl"), description="JSONL log path")

    @field_validator("mcp_server_url", mode="before")
    @classmethod
    def default_mcp_url(cls, value: str | None) -> str:
        return value.strip() if value and value.strip() else "https://api.wallex.ir/mcp"

    @field_validator("trading_mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        value = value.lower()
        if value not in {"shadow", "live"}:
            raise ValueError("TRADING_MODE must be shadow or live")
        return value

    @property
    def live_execution_allowed(self) -> bool:
        return self.trading_mode == "live" and self.enable_live_trading

    @property
    def model_api_key(self) -> SecretStr | None:
        return self.boxapi_api_key or self.openai_api_key

    @property
    def model_base_url(self) -> str | None:
        return self.boxapi_api_url_base if self.boxapi_api_key else None
