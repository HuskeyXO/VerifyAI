
import os
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from app.services.news.base import NewsProvider

load_dotenv()

MAX_CONTENT_CHARS = 20_000


class TavilyProvider(NewsProvider):
    """Search the web using Tavily and normalize results for VerifyAI."""

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")

        if not self.api_key:
            raise ValueError("TAVILY_API_KEY is not configured")

    def search_articles(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict]:
        payload = {
            "query": query,
            "topic": "general",
            "search_depth": "basic",
            "max_results": min(max(1, max_results), 10),
            "include_raw_content": "text",
            "include_answer": False,
        }

        response = requests.post(
            self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not isinstance(results, list):
            return []

        articles = []

        for item in results:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            url = item.get("url")

            if not isinstance(title, str) or not title.strip():
                continue

            if not isinstance(url, str):
                continue

            parsed_url = urlparse(url)

            if (
                parsed_url.scheme not in {"http", "https"}
                or not parsed_url.hostname
            ):
                continue

            description = (item.get("content") or "").strip()
            raw_content = (item.get("raw_content") or "").strip()

            # Keep the fuller text when Tavily provides it.
            content = (raw_content or description)[:MAX_CONTENT_CHARS]

            hostname = parsed_url.hostname.lower()
            source_name = hostname.removeprefix("www.")
            source_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            articles.append({
                "title": title.strip(),
                "description": description,
                "content": content,
                "url": url,
                "publishedAt": item.get("published_date"),
                "source": {
                    "name": source_name,
                    "url": source_url,
                },
            })

        return articles[:max_results]
