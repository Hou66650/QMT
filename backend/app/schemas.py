from datetime import date, datetime
from typing import Literal

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


class PaperOrderRequest(BaseModel):
    code: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0, le=1_000_000)

    @field_validator("code")
    @classmethod
    def normalize_order_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value or len(value) > 16:
            raise ValueError("股票代码格式不正确")
        return value


class PaperOrder(BaseModel):
    id: str
    code: str
    name: str
    side: Literal["buy", "sell"]
    quantity: int
    price: float
    amount: float
    realized_pnl: float = 0
    executed_at: datetime
    provider: str
    is_mock: bool


class PaperPosition(BaseModel):
    code: str
    name: str
    quantity: int
    average_cost: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float


class PaperAccount(BaseModel):
    mode: Literal["paper"] = "paper"
    initial_cash: float
    cash: float
    market_value: float
    total_assets: float
    total_pnl: float
    positions: list[PaperPosition]
    orders_count: int
    real_trading_enabled: bool = False


class PaperOrderResponse(BaseModel):
    order: PaperOrder
    account: PaperAccount


class HealthResponse(BaseModel):
    status: str
    provider: str
    provider_connected: bool
    is_mock: bool
    trading_enabled: bool = Field(default=False)
    paper_trading_enabled: bool = Field(default=True)
    cache: str = "memory"
