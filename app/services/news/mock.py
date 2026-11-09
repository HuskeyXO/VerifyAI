
from app.services.news.base import NewsProvider


class MockNewsProvider(NewsProvider):
    """Return synthetic articles for local pipeline testing only."""

    def search_articles(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict]:

        articles = [
            {
                "title": "Apple announces price changes for selected products in India",
                "description": (
                    "TEST DATA: Synthetic report about fictional "
                    "Apple product price changes."
                ),
                "content": (
                    "TEST DATA: This is a synthetic article for local "
                    "background-worker testing only. Mock News One reports, "
                    "in a fictional scenario, that Apple raised prices for "
                    "selected products sold in India after reviewing import "
                    "costs and distribution expenses. The invented report "
                    "says revised price tags took effect during the stated "
                    "test period and were communicated to authorised "
                    "retailers. No real reporting or source verification "
                    "supports this scenario. This sample exists solely "
                    "to exercise article extraction bypass, exact-quotation "
                    "validation, evidence persistence, source linkage, and "
                    "deterministic report generation. Do not treat this as "
                    "factual news."
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
                    "TEST DATA: Synthetic report about fictional "
                    "Apple retail prices remaining unchanged."
                ),
                "content": (
                    "TEST DATA: This is a separate synthetic article for "
                    "local background-worker testing only. Mock News Two "
                    "describes an invented retailer update in which "
                    "participating stores kept the listed prices of selected "
                    "Apple products in India unchanged during the test "
                    "period. The fictional account attributes the decision "
                    "to existing stock and unchanged supplier invoices, "
                    "and says no revised consumer price list was issued. "
                    "No real reporting or source verification supports "
                    "this scenario. This sample exists solely to exercise "
                    "article persistence, quotation validation, "
                    "contradictory evidence storage, source linkage, and "
                    "deterministic report generation. Do not treat this "
                    "as factual news."
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
