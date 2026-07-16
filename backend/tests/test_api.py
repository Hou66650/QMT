from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

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
