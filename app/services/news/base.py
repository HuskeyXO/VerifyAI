from abc import ABC, abstractmethod

class NewsProvider(ABC):

    @abstractmethod
    def search_articles(self, query: str, max_results: int = 10) -> list[dict]:
        pass
