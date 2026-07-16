import asyncio
from datetime import date
from typing import Callable, TypeVar

from app.config import Settings
from app.providers.base import MarketDataProvider
from app.providers.fallback import FallbackProvider
from app.schemas import HistoryResponse, Quote, StockInfo, TradeDay

from .cache import TTLCache
from .indicators import add_bollinger_bands, strategy_signal

T = TypeVar("T")


class MarketDataService:
    def __init__(self, provider: MarketDataProvider, settings: Settings):
        self.provider = provider
        self.settings = settings
        self.cache = TTLCache()

    async def _run(self, operation: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(self.settings.request_retries + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(operation), timeout=self.settings.request_timeout_seconds
                )
            except (TimeoutError, ConnectionError, RuntimeError) as exc:
                last_error = exc
                if attempt < self.settings.request_retries:
                    await asyncio.sleep(0.25 * (2**attempt))
        assert last_error is not None
        raise last_error

    async def get_quote(self, code: str) -> Quote:
        key = f"quote:{code.upper()}"
        cached = self.cache.get(key)
        if cached:
            return cached
        quote = await self._run(lambda: self.provider.get_quote(code))
        self.cache.set(key, quote, self.settings.quote_cache_seconds)
        return quote

    async def get_history(self, code: str, start: date, end: date, period: str) -> HistoryResponse:
        if start > end:
            raise ValueError("start 不能晚于 end")
        key = f"history:{code.upper()}:{start}:{end}:{period}"
        cached = self.cache.get(key)
        if cached:
            return cached
        source = self.provider
        if isinstance(self.provider, FallbackProvider):
            items, source = await self._run(
                lambda: self.provider.get_history_with_source(code, start, end, period)
            )
        else:
            items = await self._run(lambda: self.provider.get_history(code, start, end, period))
        items = add_bollinger_bands(items)
        signal, reason = strategy_signal(items)
        response = HistoryResponse(
            code=code.upper(), period=period, provider=source.name,
            is_mock=source.is_mock, signal=signal, signal_reason=reason, items=items,
        )
        self.cache.set(key, response, self.settings.history_cache_seconds)
        return response

    async def get_stock_list(self) -> list[StockInfo]:
        key = "stock-list"
        cached = self.cache.get(key)
        if cached:
            return cached
        items = await self._run(self.provider.get_stock_list)
        self.cache.set(key, items, 3600)
        return items

    async def get_trade_calendar(self, start: date, end: date) -> list[TradeDay]:
        if start > end:
            raise ValueError("start 不能晚于 end")
        key = f"trade-calendar:{start}:{end}"
        cached = self.cache.get(key)
        if cached:
            return cached
        items = await self._run(lambda: self.provider.get_trade_calendar(start, end))
        self.cache.set(key, items, 3600)
        return items
