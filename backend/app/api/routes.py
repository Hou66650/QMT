import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import settings
from app.schemas import HealthResponse, HistoryResponse, Quote, StockInfo, TradeDay, WatchlistItem

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
async def health():
    from app.main import market_service

    state = market_service.provider.health()
    return HealthResponse(
        status="ok", provider=str(state["name"]), provider_connected=bool(state["connected"]),
        is_mock=bool(state["is_mock"]), trading_enabled=False,
    )


@router.get("/api/stocks/{code}/quote", response_model=Quote)
async def quote(code: str):
    from app.main import market_service
    return await market_service.get_quote(code)


@router.get("/api/stocks", response_model=list[StockInfo])
async def stocks(
    query: str = Query(default="", max_length=30),
    limit: int = Query(default=50, ge=1, le=500),
):
    from app.main import market_service

    items = await market_service.get_stock_list()
    needle = query.strip().lower()
    if needle:
        items = [item for item in items if needle in item.code.lower() or needle in item.name.lower()]
    return items[:limit]


@router.get("/api/trade-calendar", response_model=list[TradeDay])
async def trade_calendar(
    start: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end: date = Query(default_factory=lambda: date.today() + timedelta(days=30)),
):
    from app.main import market_service
    return await market_service.get_trade_calendar(start, end)


@router.get("/api/stocks/{code}/history", response_model=HistoryResponse)
async def history(
    code: str,
    start: date = Query(default_factory=lambda: date.today() - timedelta(days=120)),
    end: date = Query(default_factory=date.today),
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
):
    from app.main import market_service
    return await market_service.get_history(code, start, end, period)


@router.get("/api/watchlist", response_model=list[WatchlistItem])
async def get_watchlist():
    from app.main import watchlist_service
    return watchlist_service.list()


@router.post("/api/watchlist", response_model=list[WatchlistItem], status_code=201)
async def add_watchlist(item: WatchlistItem):
    from app.main import watchlist_service
    return watchlist_service.add(item)


@router.delete("/api/watchlist/{code}", response_model=list[WatchlistItem])
async def delete_watchlist(code: str):
    from app.main import watchlist_service
    return watchlist_service.delete(code)


@router.websocket("/ws/quotes")
async def quote_stream(websocket: WebSocket):
    from app.main import market_service, watchlist_service
    await websocket.accept()
    try:
        while True:
            codes = [item.code for item in watchlist_service.list()]
            quotes = await asyncio.gather(
                *(market_service.get_quote(code) for code in codes), return_exceptions=True
            )
            payload = [quote.model_dump(mode="json") for quote in quotes if isinstance(quote, Quote)]
            await websocket.send_json({"type": "quotes", "provider": market_service.provider.name, "items": payload})
            await asyncio.sleep(settings.websocket_interval_seconds)
    except WebSocketDisconnect:
        return
