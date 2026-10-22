"""Configuration comes only from environment variables and .env; no CLI parsing."""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr | None = None
    boxapi_api_key: SecretStr | None = None
    boxapi_api_url_base: str = "https://ai.boxapi.ir/ai/v1"
    wallex_api_key: SecretStr | None = None
    mcp_server_url: str = "https://api.wallex.ir/mcp"
    ai_model: str = "gpt-5-mini"
    log_level: str = "INFO"
    trading_mode: str = "shadow"
    enable_live_trading: bool = False
    symbol: str = "BTCUSDT"
    candle_resolution: str = "60"
    candle_count: int = Field(default=120, ge=50, le=1000)
    poll_interval_seconds: int = Field(default=300, ge=30)
    risk_per_trade: float = Field(default=0.005, gt=0, le=0.02)
    max_daily_loss_fraction: float = Field(default=0.02, gt=0, le=0.1)
    max_position_fraction: float = Field(default=0.10, gt=0, le=0.25)
    stop_loss_atr: float = Field(default=1.5, gt=0, le=5)
    take_profit_atr: float = Field(default=2.5, gt=0, le=8)
    decision_log_path: Path = Path("data/decision_log.jsonl")

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
