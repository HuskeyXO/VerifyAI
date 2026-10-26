
from app.services.news.base import NewsProvider


class MockNewsProvider(NewsProvider):
    """Return sample news records for local pipeline testing."""

    def search_articles(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict]:
        articles = [
            {
                "title": "Apple announces price changes for selected products in India",
                "description": (
                    "TEST DATA: This sample article represents a report "
                    "about Apple changing selected product prices in India."
                ),
                "content": (
                    "TEST DATA ONLY. No real news article was retrieved."
                ),
                "url": "https://mock-news.example/articles/apple-prices-india-1",
                "publishedAt": "2026-10-20T10:00:00Z",
                "source": {
                    "name": "Mock News One",
                    "url": "https://mock-news-one.example",
                },
            },
            {
                "title": "Apple India prices remain unchanged, retailer says",
                "description": (
                    "TEST DATA: This sample article represents a report "
                    "claiming selected Apple product prices have not changed."
                ),
                "content": (
                    "TEST DATA ONLY. No real news article was retrieved."
                ),
                "url": "https://mock-news.example/articles/apple-prices-india-2",
                "publishedAt": "2026-10-19T10:00:00Z",
                "source": {
                    "name": "Mock News Two",
                    "url": "https://mock-news-two.example",
                },
            },
        ]

        return articles[:max_results]
