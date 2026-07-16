from app.config import Settings

from .akshare import AkShareProvider
from .base import MarketDataProvider
from .fallback import FallbackProvider
from .mock import MockProvider
from .tushare import TushareProvider


def create_provider(settings: Settings) -> MarketDataProvider:
    providers = {
        "mock": lambda: MockProvider(),
        "akshare": lambda: AkShareProvider(),
        "tushare": lambda: TushareProvider(settings.tushare_token),
    }
    try:
        primary = providers[settings.market_data_provider]()
    except KeyError as exc:
        raise ValueError(f"未知数据源 {settings.market_data_provider}") from exc
    if settings.market_data_provider != "mock" and settings.market_data_fallback_provider == "mock":
        return FallbackProvider(primary, MockProvider())
    return primary
