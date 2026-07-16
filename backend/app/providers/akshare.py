from datetime import date, datetime

from app.schemas import HistoryBar, Quote, StockInfo, TradeDay

from .base import MarketDataProvider
from .mock import normalize_code


class AkShareProvider(MarketDataProvider):
    name = "AkShareProvider"

    @staticmethod
    def _ak():
        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError("AkShare 未安装，请执行 pip install -r requirements.txt") from exc
        return ak

    def get_quote(self, code: str) -> Quote:
        code = normalize_code(code)
        frame = self._ak().stock_zh_a_spot_em()
        row = frame.loc[frame["代码"].astype(str).str.zfill(6) == code]
        if row.empty:
            raise ValueError(f"未找到股票 {code}")
        item = row.iloc[0]
        price = float(item["最新价"])
        change = float(item["涨跌额"])
        previous = price - change
        return Quote(
            code=code,
            name=str(item["名称"]),
            price=price,
            previous_close=round(previous, 3),
            change=change,
            change_percent=float(item["涨跌幅"]),
            open=float(item["今开"]),
            high=float(item["最高"]),
            low=float(item["最低"]),
            volume=float(item["成交量"]),
            amount=float(item["成交额"]),
            timestamp=datetime.now(),
            provider=self.name,
            is_mock=False,
        )

    def get_history(
        self, code: str, start: date, end: date, period: str = "daily"
    ) -> list[HistoryBar]:
        if period == "hourly":
            frame = self._ak().stock_zh_a_hist_min_em(
                symbol=normalize_code(code),
                period="60",
                start_date=f"{start.isoformat()} 09:30:00",
                end_date=f"{end.isoformat()} 15:00:00",
                adjust="qfq",
            )
            return [
                HistoryBar(
                    date=row["时间"], open=float(row["开盘"]), high=float(row["最高"]),
                    low=float(row["最低"]), close=float(row["收盘"]),
                    volume=float(row["成交量"]), amount=float(row["成交额"]),
                )
                for _, row in frame.iterrows()
            ]
        period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
        if period not in period_map:
            raise ValueError("period 仅支持 hourly、daily、weekly、monthly")
        frame = self._ak().stock_zh_a_hist(
            symbol=normalize_code(code),
            period=period_map[period],
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
        return [
            HistoryBar(
                date=row["日期"], open=float(row["开盘"]), high=float(row["最高"]),
                low=float(row["最低"]), close=float(row["收盘"]),
                volume=float(row["成交量"]), amount=float(row["成交额"]),
            )
            for _, row in frame.iterrows()
        ]

    def get_stock_list(self) -> list[StockInfo]:
        frame = self._ak().stock_zh_a_spot_em()
        return [
            StockInfo(code=str(row["代码"]).zfill(6), name=str(row["名称"]))
            for _, row in frame.iterrows()
        ]

    def get_trade_calendar(
        self, start: date | None = None, end: date | None = None
    ) -> list[TradeDay]:
        frame = self._ak().tool_trade_date_hist_sina()
        dates = [value.date() if hasattr(value, "date") else value for value in frame["trade_date"]]
        return [TradeDay(date=value, is_open=True) for value in dates if (not start or value >= start) and (not end or value <= end)]
