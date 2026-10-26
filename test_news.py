
from app.services.news.service import get_news_provider
from app.services.news.mock import MockNewsProvider


def test_mock_news_provider_returns_articles(monkeypatch):
    monkeypatch.setenv("NEWS_PROVIDER", "mock")

    provider = get_news_provider()

    assert isinstance(provider, MockNewsProvider)

    articles = provider.search_articles(
        "Apple prices India",
        max_results=5,
    )

    assert len(articles) == 2
    assert articles[0]["title"]
    assert articles[0]["url"].startswith(
        "https://mock-news.example/"
    )
