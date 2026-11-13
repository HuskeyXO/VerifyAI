import os

from app.services.news.base import NewsProvider
from app.services.news.cached import CachedNewsProvider
from app.services.news.gnews import GNewsProvider
from app.services.news.mock import MockNewsProvider
from app.services.news.tavily import TavilyProvider


def get_news_provider() -> NewsProvider:
    provider_name = os.getenv(
        "NEWS_PROVIDER",
        "gnews",
    ).strip().lower()

    if provider_name == "gnews":
        provider = GNewsProvider()

    elif provider_name == "tavily":
        provider = TavilyProvider()

    elif provider_name == "mock":
        # Keep mock responses deterministic and uncached.
        return MockNewsProvider()

    else:
        raise ValueError(
            f"Unsupported news provider: {provider_name}"
        )

    return CachedNewsProvider(provider)