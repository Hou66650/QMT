from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class Quote(BaseModel):
    code: str
    name: str
    price: float
    previous_close: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    volume: float
    amount: float
    timestamp: datetime
    provider: str
    is_mock: bool


class HistoryBar(BaseModel):
    date: datetime | date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0
    middle_band: float | None = None
    upper_band: float | None = None
    lower_band: float | None = None


class HistoryResponse(BaseModel):
    code: str
    period: str
    provider: str
    is_mock: bool
    signal: str
    signal_reason: str
    items: list[HistoryBar]


class StockInfo(BaseModel):
    code: str
    name: str
    market: str = "A股"


class TradeDay(BaseModel):
    date: date
    is_open: bool


class WatchlistItem(BaseModel):
    code: str
    name: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value or len(value) > 16:
            raise ValueError("股票代码格式不正确")
        return value


class HealthResponse(BaseModel):
    status: str
    provider: str
    provider_connected: bool
    is_mock: bool
    trading_enabled: bool = Field(default=False)
    cache: str = "memory"
