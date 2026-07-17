"""Read-only iFinD HTTP adapter for container-friendly deployments."""

from __future__ import annotations

from datetime import date, datetime
from threading import Lock
from typing import Any

import httpx

from app.schemas import HistoryBar, Quote, StockInfo, TradeDay

from .base import MarketDataProvider
from .mock import normalize_code


class IfindProvider(MarketDataProvider):
    """Use refresh_token -> in-memory access_token; no credentials are logged."""

    name = "iFinDProvider"
    is_mock = False

    def __init__(
        self,
        refresh_token: str | None,
        base_url: str = "https://quantapi.51ifind.com/api/v1",
        timeout_seconds: float = 8,
        client: httpx.Client | None = None,
    ):
        if not refresh_token:
            raise RuntimeError("选择 iFinDProvider 时必须配置 IFIND_REFRESH_TOKEN")
        self._refresh_token = refresh_token
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._access_token: str | None = None
        self._token_lock = Lock()

    @staticmethod
    def _ifind_code(code: str) -> str:
        code = normalize_code(code)
        return f"{code}.SH" if code.startswith(("5", "6", "9")) else f"{code}.SZ"

    @staticmethod
    def _first(value: Any, index: int = 0) -> Any:
        return value[index] if isinstance(value, (list, tuple)) and index < len(value) else value

    @staticmethod
    def _number(value: Any, default: float = 0) -> float:
        value = IfindProvider._first(value)
        if value in (None, "", "--", "null", "None"):
            return default
        try:
            return float(str(value).replace(",", "").replace("%", "").strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"iFinD 返回了不可识别的数值: {value!r}") from exc

    @staticmethod
    def _datetime(value: Any) -> datetime:
        value = str(IfindProvider._first(value)).strip()
        for parser in (datetime.fromisoformat, lambda item: datetime.strptime(item, "%Y%m%d")):
            try:
                return parser(value)
            except ValueError:
                continue
        raise ValueError(f"iFinD 返回了不可识别的时间: {value!r}")

    @staticmethod
    def _error(payload: dict[str, Any]) -> str | None:
        code = payload.get("errorcode", payload.get("errorCode"))
        if code not in (None, 0, "0"):
            return f"{code}: {payload.get('errmsg') or payload.get('errorMsg') or 'unknown error'}"
        return None

    def _post_raw(self, endpoint: str, headers: dict[str, str], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self._client.post(f"{self._base_url}/{endpoint}", headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError("iFinD 请求超时") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise RuntimeError("iFinD token authentication failed") from exc
            raise ConnectionError("iFinD HTTP 请求失败") from exc
        except httpx.HTTPError as exc:
            raise ConnectionError("iFinD 网络请求失败") from exc
        except ValueError as exc:
            raise RuntimeError("iFinD 返回了无效 JSON") from exc
        if not isinstance(body, dict):
            raise RuntimeError("iFinD 返回了无效响应")
        if error := self._error(body):
            raise RuntimeError(f"iFinD 请求失败: {error}")
        return body

    def _token(self, force: bool = False) -> str:
        with self._token_lock:
            if self._access_token and not force:
                return self._access_token
            body = self._post_raw(
                "get_access_token", {"Content-Type": "application/json", "refresh_token": self._refresh_token}
            )
            data = body.get("data")
            token = data.get("access_token") if isinstance(data, dict) else None
            if not token:
                raise RuntimeError("iFinD 未返回 access_token，请检查接口权限或 refresh token")
            self._access_token = str(token)
            return self._access_token

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        for refresh in (False, True):
            token = self._token(force=refresh)
            try:
                return self._post_raw(
                    endpoint,
                    {"Content-Type": "application/json", "access_token": token, "ifindlang": "cn"},
                    payload,
                )
            except RuntimeError as exc:
                if not refresh and any(word in str(exc).lower() for word in ("token", "auth", "鉴权", "权限")):
                    self._access_token = None
                    continue
                raise
        raise RuntimeError("iFinD access_token 刷新失败")

    @staticmethod
    def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        tables = payload.get("tables") or []
        if isinstance(tables, dict):
            tables = [tables]
        result: list[dict[str, Any]] = []
        for source in tables:
            if not isinstance(source, dict):
                continue
            table = source.get("table", source)
            if not isinstance(table, dict):
                continue
            widths = [len(value) for value in table.values() if isinstance(value, list)]
            widths.extend(len(value) for value in source.values() if isinstance(value, list))
            for index in range(max(widths, default=1)):
                row = {key: IfindProvider._first(value, index) for key, value in source.items() if key != "table"}
                row.update({key: IfindProvider._first(value, index) for key, value in table.items()})
                result.append(row)
        return result

    @staticmethod
    def _value(row: dict[str, Any], *names: str) -> Any:
        values = {str(key).lower(): value for key, value in row.items()}
        for name in names:
            if (value := values.get(name.lower())) not in (None, "", "--"):
                return value
        return None

    @staticmethod
    def _resample(bars: list[HistoryBar], period: str) -> list[HistoryBar]:
        if period == "daily":
            return bars
        grouped: dict[tuple[int, int], list[HistoryBar]] = {}
        for bar in bars:
            bar_date = bar.date.date() if isinstance(bar.date, datetime) else bar.date
            key = (bar_date.isocalendar().year, bar_date.isocalendar().week) if period == "weekly" else (bar_date.year, bar_date.month)
            grouped.setdefault(key, []).append(bar)
        return [
            HistoryBar(
                date=items[-1].date, open=items[0].open, high=max(item.high for item in items),
                low=min(item.low for item in items), close=items[-1].close,
                volume=sum(item.volume for item in items), amount=sum(item.amount for item in items),
            )
            for items in grouped.values()
        ]

    def get_quote(self, code: str) -> Quote:
        normalized = normalize_code(code)
        payload = self._post(
            "real_time_quotation",
            {"codes": self._ifind_code(normalized), "indicators": "open,high,low,latest,preClose,change,changeRatio,volume,amount,thsname"},
        )
        rows = self._rows(payload)
        if not rows:
            raise ValueError(f"iFinD 未返回股票 {normalized} 的行情")
        row = rows[0]
        price = self._number(self._value(row, "latest", "close", "price"))
        previous = self._number(self._value(row, "preClose", "preclose", "previousClose"), price)
        change = self._number(self._value(row, "change"), price - previous)
        change_percent = self._number(self._value(row, "changeRatio", "pctChg"), change / previous * 100 if previous else 0)
        timestamp = self._value(row, "time", "timestamp", "datetime")
        return Quote(
            code=normalized, name=str(self._value(row, "thsname", "name", "secname") or normalized),
            price=price, previous_close=previous, change=change, change_percent=change_percent,
            open=self._number(self._value(row, "open"), price), high=self._number(self._value(row, "high"), price),
            low=self._number(self._value(row, "low"), price), volume=self._number(self._value(row, "volume", "vol")),
            amount=self._number(self._value(row, "amount", "turnover")),
            timestamp=self._datetime(timestamp) if timestamp else datetime.now(), provider=self.name, is_mock=False,
        )

    def get_history(self, code: str, start: date, end: date, period: str = "daily") -> list[HistoryBar]:
        if period not in {"hourly", "daily", "weekly", "monthly"}:
            raise ValueError("period 仅支持 hourly、daily、weekly、monthly")
        payload: dict[str, Any] = {"codes": self._ifind_code(code), "indicators": "open,high,low,close,volume,amount"}
        endpoint = "high_frequency" if period == "hourly" else "cmd_history_quotation"
        if period == "hourly":
            payload.update({"starttime": f"{start} 09:30:00", "endtime": f"{end} 15:00:00", "functionpara": {"Interval": "60", "Fill": "Blank"}})
        else:
            payload.update({"startdate": start.isoformat(), "enddate": end.isoformat(), "functionpara": {"Fill": "Blank"}})
        bars = []
        for row in self._rows(self._post(endpoint, payload)):
            timestamp = self._value(row, "time", "date", "datetime", "tradeDate")
            if not timestamp:
                continue
            parsed = self._datetime(timestamp)
            bars.append(HistoryBar(
                date=parsed if period == "hourly" else parsed.date(), open=self._number(self._value(row, "open")),
                high=self._number(self._value(row, "high")), low=self._number(self._value(row, "low")),
                close=self._number(self._value(row, "close", "latest")), volume=self._number(self._value(row, "volume", "vol")),
                amount=self._number(self._value(row, "amount", "turnover")),
            ))
        if not bars:
            raise ValueError("iFinD 未返回历史行情，请检查账号权限或交易日期")
        bars.sort(key=lambda bar: bar.date)
        return self._resample(bars, period) if period in {"weekly", "monthly"} else bars

    def get_stock_list(self) -> list[StockInfo]:
        payload = self._post("data_pool", {
            "reportname": "p03425",
            "functionpara": {"date": date.today().strftime("%Y%m%d"), "blockname": "001005010", "iv_type": "allcontract"},
            "outputpara": "p03291_f001,p03291_f002",
        })
        stocks = [
            StockInfo(code=normalize_code(str(code)), name=str(name))
            for row in self._rows(payload)
            if (code := self._value(row, "thscode", "code", "p03291_f001"))
            and (name := self._value(row, "thsname", "name", "p03291_f002"))
        ]
        if not stocks:
            raise ValueError("iFinD 未返回股票列表，请检查 data_pool 权限")
        return stocks

    def get_trade_calendar(self, start: date | None = None, end: date | None = None) -> list[TradeDay]:
        start = start or date.today()
        end = end or start
        payload = self._post("get_trade_dates", {
            "marketcode": "212001", "functionpara": {"dateType": "0", "period": "D", "dateFormat": "0", "output": "sequencedate"},
            "startdate": start.isoformat(), "enddate": end.isoformat(),
        })
        dates = set()
        for row in self._rows(payload):
            for key, value in row.items():
                if "date" in str(key).lower() and value:
                    dates.add(self._datetime(value).date())
        return [TradeDay(date=value, is_open=True) for value in sorted(dates) if start <= value <= end]
