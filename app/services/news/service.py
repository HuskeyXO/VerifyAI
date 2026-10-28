
import os

from app.services.news.base import NewsProvider
from app.services.news.gnews import GNewsProvider
from app.services.news.mock import MockNewsProvider
from app.services.news.tavily import TavilyProvider



def get_news_provider() -> NewsProvider:
    provider_name = os.getenv(
        "NEWS_PROVIDER",
        "gnews",
    ).strip().lower()

    if provider_name == "gnews":
        return GNewsProvider()

    if provider_name == "tavily":
        return TavilyProvider()

    if provider_name == "mock":
        return MockNewsProvider()

    raise ValueError(
        f"Unsupported news provider: {provider_name}"
    )

