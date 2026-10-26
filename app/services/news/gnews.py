
import os
import time
from threading import Lock

import requests
from dotenv import load_dotenv

from app.services.news.base import NewsProvider

load_dotenv()

_request_lock = Lock()
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 1.1


class GNewsProvider(NewsProvider):
    BASE_URL = "https://gnews.io/api/v4/search"

    def __init__(self):
        self.api_key = os.getenv("GNEWS_API_KEY")

        if not self.api_key:
            raise ValueError("GNEWS_API_KEY is not configured")

    def search_articles(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict]:
        global _last_request_time

        params = {
            "q": query,
            "lang": "en",
            "max": min(max_results, 10),
        }

        with _request_lock:
            delay = _MIN_REQUEST_INTERVAL - (
                time.monotonic() - _last_request_time
            )

            if delay > 0:
                time.sleep(delay)

            _last_request_time = time.monotonic()

            response = requests.get(
                self.BASE_URL,
                params=params,
                headers={"X-Api-Key": self.api_key},
                timeout=10,
            )

        response.raise_for_status()
        return response.json().get("articles", [])
