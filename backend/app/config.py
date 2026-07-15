import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "天玑300量化研究系统")
    environment: str = os.getenv("ENVIRONMENT", "development")
    market_data_provider: str = os.getenv("MARKET_DATA_PROVIDER", "mock").lower()
    tushare_token: str | None = os.getenv("TUSHARE_TOKEN")
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "8"))
    request_retries: int = int(os.getenv("REQUEST_RETRIES", "2"))
    quote_cache_seconds: int = int(os.getenv("QUOTE_CACHE_SECONDS", "5"))
    history_cache_seconds: int = int(os.getenv("HISTORY_CACHE_SECONDS", "300"))
    websocket_interval_seconds: float = float(os.getenv("WEBSOCKET_INTERVAL_SECONDS", "3"))
    watchlist_file: Path = Path(os.getenv("WATCHLIST_FILE", "data/watchlist.json"))
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    trading_enabled: bool = _bool("TRADING_ENABLED", False)

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
