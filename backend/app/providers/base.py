from abc import ABC, abstractmethod
from datetime import date

from app.schemas import HistoryBar, Quote, StockInfo, TradeDay


class MarketDataProvider(ABC):
    """所有行情实现必须遵守的稳定边界。"""

    name: str
    is_mock: bool = False

    @abstractmethod
    def get_quote(self, code: str) -> Quote: ...

    @abstractmethod
    def get_history(
        self, code: str, start: date, end: date, period: str = "daily"
    ) -> list[HistoryBar]: ...

    @abstractmethod
    def get_stock_list(self) -> list[StockInfo]: ...

    @abstractmethod
    def get_trade_calendar(
        self, start: date | None = None, end: date | None = None
    ) -> list[TradeDay]: ...

    def health(self) -> dict[str, str | bool]:
        return {"name": self.name, "connected": True, "is_mock": self.is_mock}
