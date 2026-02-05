"""
配置管理模組
使用pydantic-settings進行環境變數管理
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """應用配置"""

    # Database
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="crypto", alias="POSTGRES_USER")
    postgres_password: str = Field(default="crypto_pass", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="crypto_db", alias="POSTGRES_DB")

    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    # Bybit API (Primary)
    bybit_api_key: str = Field(default="", alias="BYBIT_API_KEY")
    bybit_api_secret: str = Field(default="", alias="BYBIT_API_SECRET")

    # Binance API (Secondary)
    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", alias="BINANCE_API_SECRET")

    # Telegram Notification
    tg_bot_token: str = Field(default="", alias="TG_BOT_TOKEN")
    tg_chat_id: str = Field(default="", alias="TG_CHAT_ID")

    # Collector
    collector_interval_seconds: int = Field(default=60, alias="COLLECTOR_INTERVAL_SECONDS")
    default_timeframe: str = Field(default="1m", alias="DEFAULT_TIMEFRAME")
    default_limit: int = Field(default=1000, alias="DEFAULT_LIMIT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """返回完整的資料庫連接字串"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """返回Redis連接字串"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# 全域配置實例
settings = Settings()
