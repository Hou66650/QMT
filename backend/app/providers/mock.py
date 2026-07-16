import hashlib
import math
import random
from datetime import date, datetime, time, timedelta

from app.schemas import HistoryBar, Quote, StockInfo, TradeDay

from .base import MarketDataProvider


STOCKS = {
    "000001": "平安银行",
    "000858": "五粮液",
    "300750": "宁德时代",
    "600036": "招商银行",
    "600519": "贵州茅台",
    "601318": "中国平安",
}


def normalize_code(code: str) -> str:
    return code.upper().replace(".SH", "").replace(".SZ", "").strip()


class MockProvider(MarketDataProvider):
    name = "MockProvider"
    is_mock = True

    @staticmethod
    def _seed(code: str) -> int:
        return int(hashlib.sha256(code.encode()).hexdigest()[:8], 16)

    def get_quote(self, code: str) -> Quote:
        code = normalize_code(code)
        rng = random.Random(self._seed(code) + date.today().toordinal())
        base = 12 + self._seed(code) % 48000 / 100
        previous = round(base, 2)
        pct = rng.uniform(-0.035, 0.045)
        price = round(previous * (1 + pct), 2)
        high = round(max(price, previous) * (1 + rng.uniform(0.002, 0.018)), 2)
        low = round(min(price, previous) * (1 - rng.uniform(0.002, 0.018)), 2)
        volume = float(rng.randint(200_000, 8_000_000))
        return Quote(
            code=code,
            name=STOCKS.get(code, f"模拟股票 {code}"),
            price=price,
            previous_close=previous,
            change=round(price - previous, 2),
            change_percent=round((price / previous - 1) * 100, 2),
            open=round(previous * (1 + rng.uniform(-0.01, 0.01)), 2),
            high=high,
            low=low,
            volume=volume,
            amount=round(volume * price, 2),
            timestamp=datetime.now(),
            provider=self.name,
            is_mock=True,
        )

    def get_history(
        self, code: str, start: date, end: date, period: str = "daily"
    ) -> list[HistoryBar]:
        if period not in {"hourly", "daily", "weekly", "monthly"}:
            raise ValueError("period 仅支持 hourly、daily、weekly、monthly")
        code = normalize_code(code)
        rng = random.Random(self._seed(code) + start.toordinal())
        current = 12 + self._seed(code) % 48000 / 100
        result: list[HistoryBar] = []
        day = start
        index = 0
        if period == "hourly":
            slots = ((10, 30), (11, 30), (14, 0), (15, 0))
            while day <= end:
                if day.weekday() < 5:
                    for hour, minute in slots:
                        drift = math.sin(index / 7) * 0.004 + rng.uniform(-0.012, 0.012)
                        open_price = current * (1 + rng.uniform(-0.004, 0.004))
                        close = max(1, open_price * (1 + drift))
                        high = max(open_price, close) * (1 + rng.uniform(0.001, 0.008))
                        low = min(open_price, close) * (1 - rng.uniform(0.001, 0.008))
                        volume = float(rng.randint(50_000, 2_000_000))
                        result.append(HistoryBar(date=datetime.combine(day, time(hour, minute)), open=round(open_price, 2), high=round(high, 2), low=round(low, 2), close=round(close, 2), volume=volume, amount=round(volume * close, 2)))
                        current = close
                        index += 1
                day += timedelta(days=1)
            return result[-120:]
        while day <= end:
            if day.weekday() < 5:
                drift = math.sin(index / 8) * 0.006 + rng.uniform(-0.022, 0.022)
                open_price = current * (1 + rng.uniform(-0.008, 0.008))
                close = max(1, open_price * (1 + drift))
                high = max(open_price, close) * (1 + rng.uniform(0.003, 0.018))
                low = min(open_price, close) * (1 - rng.uniform(0.003, 0.018))
                volume = float(rng.randint(200_000, 8_000_000))
                result.append(
                    HistoryBar(
                        date=day,
                        open=round(open_price, 2),
                        high=round(high, 2),
                        low=round(low, 2),
                        close=round(close, 2),
                        volume=volume,
                        amount=round(volume * close, 2),
                    )
                )
                current = close
                index += 1
            day += timedelta(days=1)
        if period == "daily":
            return result

        grouped: dict[tuple[int, int] | tuple[int, str], list[HistoryBar]] = {}
        for bar in result:
            key = (
                (bar.date.isocalendar().year, bar.date.isocalendar().week)
                if period == "weekly"
                else (bar.date.year, f"{bar.date.month:02d}")
            )
            grouped.setdefault(key, []).append(bar)

        return [
            HistoryBar(
                date=bars[-1].date,
                open=bars[0].open,
                high=max(bar.high for bar in bars),
                low=min(bar.low for bar in bars),
                close=bars[-1].close,
                volume=sum(bar.volume for bar in bars),
                amount=sum(bar.amount for bar in bars),
            )
            for bars in grouped.values()
        ]

    def get_stock_list(self) -> list[StockInfo]:
        return [StockInfo(code=code, name=name) for code, name in STOCKS.items()]

    def get_trade_calendar(
        self, start: date | None = None, end: date | None = None
    ) -> list[TradeDay]:
        start = start or date.today() - timedelta(days=30)
        end = end or date.today() + timedelta(days=30)
        return [
            TradeDay(date=start + timedelta(days=i), is_open=(start + timedelta(days=i)).weekday() < 5)
            for i in range((end - start).days + 1)
        ]
