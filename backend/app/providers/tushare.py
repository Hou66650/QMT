from datetime import date, datetime

from app.schemas import HistoryBar, Quote, StockInfo, TradeDay

from .base import MarketDataProvider
from .mock import normalize_code


def _ts_code(code: str) -> str:
    code = normalize_code(code)
    return f"{code}.SH" if code.startswith("6") else f"{code}.SZ"


class TushareProvider(MarketDataProvider):
    name = "TushareProvider"

    def __init__(self, token: str | None):
        if not token:
            raise RuntimeError("选择 TushareProvider 时必须配置 TUSHARE_TOKEN")
        try:
            import tushare as ts
        except ImportError as exc:
            raise RuntimeError("Tushare 未安装，请执行 pip install -r requirements.txt") from exc
        self.pro = ts.pro_api(token)

    def get_quote(self, code: str) -> Quote:
        frame = self.pro.daily(ts_code=_ts_code(code), start_date=date.today().strftime("%Y%m%d"))
        if frame.empty:
            raise ValueError("Tushare 免费接口未返回当日行情；请在交易日收盘后重试")
        item = frame.iloc[0]
        return Quote(
            code=normalize_code(code), name=normalize_code(code), price=float(item["close"]),
            previous_close=float(item["pre_close"]), change=float(item["change"]),
            change_percent=float(item["pct_chg"]), open=float(item["open"]),
            high=float(item["high"]), low=float(item["low"]), volume=float(item["vol"]),
            amount=float(item["amount"]), timestamp=datetime.now(), provider=self.name, is_mock=False,
        )

    def get_history(self, code: str, start: date, end: date, period: str = "daily") -> list[HistoryBar]:
        endpoints = {
            "daily": self.pro.daily,
            "weekly": self.pro.weekly,
            "monthly": self.pro.monthly,
        }
        if period not in endpoints:
            raise ValueError("period 仅支持 daily、weekly、monthly")
        frame = endpoints[period](
            ts_code=_ts_code(code),
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
        frame = frame.sort_values("trade_date")
        return [HistoryBar(date=datetime.strptime(str(row["trade_date"]), "%Y%m%d").date(), open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"]), volume=float(row["vol"]), amount=float(row["amount"])) for _, row in frame.iterrows()]

    def get_stock_list(self) -> list[StockInfo]:
        frame = self.pro.stock_basic(exchange="", list_status="L", fields="ts_code,name,market")
        return [StockInfo(code=str(row["ts_code"]).split(".")[0], name=str(row["name"]), market=str(row["market"])) for _, row in frame.iterrows()]

    def get_trade_calendar(self, start: date | None = None, end: date | None = None) -> list[TradeDay]:
        frame = self.pro.trade_cal(exchange="SSE", start_date=start.strftime("%Y%m%d") if start else None, end_date=end.strftime("%Y%m%d") if end else None)
        return [TradeDay(date=datetime.strptime(str(row["cal_date"]), "%Y%m%d").date(), is_open=bool(row["is_open"])) for _, row in frame.iterrows()]
