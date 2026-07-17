import asyncio
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.providers.fallback import FallbackProvider
from app.providers.factory import create_provider
from app.providers.ifind import IfindProvider
from app.providers.mock import MockProvider

client = TestClient(app)


def test_health_is_safe_and_mock_by_default():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["is_mock"] is True
    assert response.json()["trading_enabled"] is False


def test_quote_contract():
    response = client.get("/api/stocks/600519/quote")
    assert response.status_code == 200
    assert response.json()["code"] == "600519"
    assert response.json()["provider"] == "MockProvider"


def test_history_contains_bollinger_and_signal():
    end = date.today()
    start = end - timedelta(days=90)
    response = client.get(f"/api/stocks/300750/history?start={start}&end={end}")
    body = response.json()
    assert response.status_code == 200
    assert body["signal"] in {"关注低吸", "注意回撤", "中性", "观察"}
    assert any(item["middle_band"] is not None for item in body["items"])


def test_history_periods_are_resampled():
    hourly = client.get("/api/stocks/600519/history?period=hourly").json()["items"]
    daily = client.get("/api/stocks/600519/history?period=daily").json()["items"]
    weekly = client.get("/api/stocks/600519/history?period=weekly").json()["items"]
    monthly = client.get("/api/stocks/600519/history?period=monthly").json()["items"]
    assert len(daily) > len(weekly) > len(monthly)
    assert len(hourly) >= 20
    assert "T" in hourly[-1]["date"]
    assert hourly[-1]["middle_band"] is not None


def test_stock_search_and_trade_calendar():
    stocks = client.get("/api/stocks?query=茅台&limit=5")
    calendar = client.get("/api/trade-calendar")
    assert stocks.status_code == 200
    assert stocks.json()[0]["code"] == "600519"
    assert calendar.status_code == 200
    assert any(day["is_open"] for day in calendar.json())


def test_watchlist_crud():
    created = client.post("/api/watchlist", json={"code": "600036", "name": "招商银行"})
    assert created.status_code == 201
    assert any(item["code"] == "600036" for item in created.json())
    deleted = client.delete("/api/watchlist/600036")
    assert all(item["code"] != "600036" for item in deleted.json())


def test_live_provider_falls_back_to_clearly_marked_mock_data():
    primary = MockProvider()
    primary.name = "UnavailableProvider"
    primary.get_quote = lambda _code: (_ for _ in ()).throw(ConnectionError("upstream unavailable"))
    quote = FallbackProvider(primary, MockProvider()).get_quote("600519")
    assert quote.provider == "MockProvider"
    assert quote.is_mock is True


def test_fallback_history_reports_the_actual_source():
    class BrokenProvider(MockProvider):
        name = "BrokenProvider"
        is_mock = False

        def get_history(self, *args, **kwargs):
            raise ConnectionError("upstream unavailable")

    from app.config import Settings
    from app.services.market_data import MarketDataService

    service = MarketDataService(
        FallbackProvider(BrokenProvider(), MockProvider()), Settings(market_data_provider="mock")
    )
    response = asyncio.run(service.get_history("600519", date(2026, 1, 1), date(2026, 1, 31), "daily"))

    assert response.provider == "MockProvider"
    assert response.is_mock is True


class _FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


class _FakeIWindClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def post(self, url, headers, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse(next(self.responses))


def test_ifind_uses_http_tokens_and_maps_quote():
    client = _FakeIWindClient([
        {"data": {"access_token": "short-lived-token"}},
        {
            "errorcode": 0,
            "tables": [{
                "time": ["2026-07-17 10:30:00"],
                "table": {
                    "thsname": ["贵州茅台"], "latest": [1500], "preClose": [1480],
                    "change": [20], "changeRatio": [1.35], "open": [1490], "high": [1510],
                    "low": [1485], "volume": [1000], "amount": [1500000],
                },
            }],
        },
    ])
    provider = IfindProvider("refresh-token", base_url="https://ifind.test/api/v1", client=client)

    quote = provider.get_quote("600519")

    assert quote.code == "600519"
    assert quote.name == "贵州茅台"
    assert quote.price == 1500
    assert quote.provider == "iFinDProvider"
    assert client.calls[0]["headers"]["refresh_token"] == "refresh-token"
    assert client.calls[1]["headers"]["access_token"] == "short-lived-token"
    assert client.calls[1]["json"]["codes"] == "600519.SH"


def test_ifind_is_registered_in_provider_factory():
    from app.config import Settings

    provider = create_provider(
        Settings(market_data_provider="ifind", ifind_refresh_token="local-test-token")
    )

    assert isinstance(provider, FallbackProvider)
    assert isinstance(provider.primary, IfindProvider)


def test_ifind_maps_history_stock_list_and_calendar():
    client = _FakeIWindClient([
        {"data": {"access_token": "short-lived-token"}},
        {
            "tables": [{"time": ["2026-01-05", "2026-01-06"], "table": {
                "open": [10, 11], "high": [12, 13], "low": [9, 10], "close": [11, 12],
                "volume": [100, 200], "amount": [1100, 2400],
            }}],
        },
        {"tables": [{"table": {"p03291_f001": ["600519.SH"], "p03291_f002": ["贵州茅台"]}}]},
        {"tables": [{"table": {"sequencedate": ["2026-01-05", "2026-01-06"]}}]},
    ])
    provider = IfindProvider("refresh-token", client=client)

    history = provider.get_history("600519", date(2026, 1, 5), date(2026, 1, 6))
    stocks = provider.get_stock_list()
    calendar = provider.get_trade_calendar(date(2026, 1, 5), date(2026, 1, 6))

    assert [bar.close for bar in history] == [11, 12]
    assert stocks[0].code == "600519"
    assert stocks[0].name == "贵州茅台"
    assert [item.date for item in calendar] == [date(2026, 1, 5), date(2026, 1, 6)]
    assert len(client.calls) == 4  # access token is cached after the first exchange
