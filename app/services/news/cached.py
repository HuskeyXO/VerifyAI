import hashlib
import json

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.services.news.base import NewsProvider


CACHE_TTL_SECONDS = 600


class CachedNewsProvider(NewsProvider):
    """Add optional Redis caching around an existing news provider."""

    def __init__(
        self,
        provider: NewsProvider,
        redis_client: Redis | None = None,
        ttl_seconds: int = CACHE_TTL_SECONDS,
    ):
        if ttl_seconds <= 0:
            raise ValueError("Cache TTL must be positive")

        self.provider = provider
        self.ttl_seconds = ttl_seconds

        self.redis = redis_client or Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
        )

    def _cache_key(self, query: str, max_results: int) -> str:
        key_data = {
            "provider": self.provider.__class__.__name__,
            "query": " ".join(query.split()),
            "max_results": max_results,
        }

        serialized = json.dumps(
            key_data,
            sort_keys=True,
            ensure_ascii=False,
        )

        digest = hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

        return f"verifyai:news:v1:{digest}"

    def search_articles(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict]:

        cache_key = self._cache_key(query, max_results)

        # Try Redis first. A cache failure must not stop verification.
        try:
            cached_data = self.redis.get(cache_key)

            if cached_data is not None:
                try:
                    articles = json.loads(cached_data)

                    if (
                        isinstance(articles, list)
                        and all(isinstance(item, dict) for item in articles)
                    ):
                        return articles

                    self.redis.delete(cache_key)

                except (ValueError, TypeError):
                    self.redis.delete(cache_key)

        except RedisError:
            pass

        # Cache miss or Redis unavailable: call the actual provider.
        articles = self.provider.search_articles(
            query,
            max_results,
        )

        # Cache only successfully returned, serializable results.
        try:
            serialized_articles = json.dumps(
                articles,
                ensure_ascii=False,
            )

            self.redis.setex(
                cache_key,
                self.ttl_seconds,
                serialized_articles,
            )

        except (RedisError, TypeError, ValueError):
            pass

        return articles