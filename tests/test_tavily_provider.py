
import pytest

from app.services.news.service import get_news_provider
from app.services.news.tavily import TavilyProvider


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_tavily_normalizes_search_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs

        return FakeResponse({
            "results": [{
                "title": "Logitech gaming mouse review",
                "url": "https://www.example.com/reviews/mouse",
                "content": "A short search snippet.",
                "raw_content": "The fuller article text.",
                "published_date": "2026-10-20",
                "score": 0.95,
            }]
        })

    monkeypatch.setattr(
        "app.services.news.tavily.requests.post",
        fake_post,
    )

    provider = TavilyProvider()
    articles = provider.search_articles(
        "Logitech gaming mouse India",
        max_results=5,
    )

    assert len(articles) == 1
    assert articles[0]["title"] == "Logitech gaming mouse review"
    assert articles[0]["description"] == "A short search snippet."
    assert articles[0]["content"] == "The fuller article text."
    assert articles[0]["source"]["name"] == "example.com"
    assert articles[0]["publishedAt"] == "2026-10-20"

    assert captured["url"] == TavilyProvider.BASE_URL
    assert captured["kwargs"]["headers"]["Authorization"] == (
        "Bearer test-key"
    )
    assert captured["kwargs"]["json"]["query"] == (
        "Logitech gaming mouse India"
    )


def test_tavily_returns_empty_list_for_no_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    monkeypatch.setattr(
        "app.services.news.tavily.requests.post",
        lambda *args, **kwargs: FakeResponse({"results": []}),
    )

    provider = TavilyProvider()

    assert provider.search_articles("some obscure claim") == []


def test_tavily_rejects_invalid_article_urls(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    monkeypatch.setattr(
        "app.services.news.tavily.requests.post",
        lambda *args, **kwargs: FakeResponse({
            "results": [
                {
                    "title": "Missing URL",
                    "content": "Some content.",
                },
                {
                    "title": "Invalid URL",
                    "url": "javascript:alert(1)",
                    "content": "Some content.",
                },
            ]
        }),
    )

    provider = TavilyProvider()

    assert provider.search_articles("test query") == []


def test_factory_selects_tavily(monkeypatch):
    monkeypatch.setenv("NEWS_PROVIDER", "tavily")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    provider = get_news_provider()

    assert isinstance(provider, TavilyProvider)


def test_tavily_requires_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        TavilyProvider()
