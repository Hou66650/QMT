import logging
from datetime import date

from app.schemas import HistoryBar, Quote, StockInfo, TradeDay

from .base import MarketDataProvider

logger = logging.getLogger(__name__)


class FallbackProvider(MarketDataProvider):
    """Use a clearly-labelled fallback when a live provider is temporarily unavailable."""

    def __init__(self, primary: MarketDataProvider, fallback: MarketDataProvider):
        self.primary = primary
        self.fallback = fallback
        self.name = primary.name
        self.is_mock = primary.is_mock

    def _call(self, operation: str, primary_call, fallback_call):
        try:
            return primary_call()
        except Exception as exc:
            logger.warning("%s failed for %s; using %s", self.primary.name, operation, self.fallback.name, exc_info=exc)
            return fallback_call()

    def get_quote(self, code: str) -> Quote:
        return self._call("quote", lambda: self.primary.get_quote(code), lambda: self.fallback.get_quote(code))

    def get_history(self, code: str, start: date, end: date, period: str = "daily") -> list[HistoryBar]:
        return self._call("history", lambda: self.primary.get_history(code, start, end, period), lambda: self.fallback.get_history(code, start, end, period))

    def get_stock_list(self) -> list[StockInfo]:
        return self._call("stock list", self.primary.get_stock_list, self.fallback.get_stock_list)

    def get_trade_calendar(self, start: date | None = None, end: date | None = None) -> list[TradeDay]:
        return self._call("trade calendar", lambda: self.primary.get_trade_calendar(start, end), lambda: self.fallback.get_trade_calendar(start, end))

    def health(self) -> dict[str, str | bool]:
        return self.primary.health()
