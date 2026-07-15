import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings
from app.providers import create_provider
from app.services.market_data import MarketDataService
from app.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)

provider = create_provider(settings)
market_service = MarketDataService(provider, settings)
watchlist_service = WatchlistService(settings.watchlist_file)

app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
app.include_router(router)


@app.exception_handler(ValueError)
async def validation_error(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"error": {"code": "BAD_REQUEST", "message": str(exc)}})


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception):
    logger.exception("Unhandled API error", exc_info=exc)
    return JSONResponse(status_code=503, content={"error": {"code": "DATA_SOURCE_ERROR", "message": "行情服务暂时不可用，请稍后重试"}})
