import json

from redis.exceptions import RedisError

from app.services.news.base import NewsProvider
from app.services.news.cached import CachedNewsProvider


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}
        self.now = 0
        self.fail_get = False
        self.fail_setex = False

    def get(self, key):
        if self.fail_get:
            raise RedisError("Redis unavailable")

        if self.expirations.get(key, float("inf")) <= self.now:
            self.values.pop(key, None)
            self.expirations.pop(key, None)

        return self.values.get(key)

    def setex(self, key, ttl, value):
        if self.fail_setex:
            raise RedisError("Redis unavailable")

        self.values[key] = value
        self.expirations[key] = self.now + ttl

    def delete(self, key):
        self.values.pop(key, None)
        self.expirations.pop(key, None)

    def advance(self, seconds):
        self.now += seconds


class FakeNewsProvider(NewsProvider):
    def __init__(self):
        self.calls = []

    def search_articles(self, query, max_results=10):
        self.calls.append((query, max_results))

        return [{
            "title": f"Result {len(self.calls)}",
            "url": "https://example.com/article",
        }]


class AnotherFakeNewsProvider(FakeNewsProvider):
    pass


def test_cache_miss_calls_provider_and_stores_results():
    redis_client = FakeRedis()
    provider = FakeNewsProvider()

    cached_provider = CachedNewsProvider(
        provider,
        redis_client=redis_client,
    )

    results = cached_provider.search_articles("test claim", 5)

    key = cached_provider._cache_key("test claim", 5)

    assert len(provider.calls) == 1
    assert json.loads(redis_client.get(key)) == results
    assert redis_client.expirations[key] == 600


def test_cache_hit_avoids_calling_provider_again():
    redis_client = FakeRedis()
    provider = FakeNewsProvider()

    cached_provider = CachedNewsProvider(
        provider,
        redis_client=redis_client,
    )

    first_result = cached_provider.search_articles("test claim", 5)
    second_result = cached_provider.search_articles("test claim", 5)

    assert first_result == second_result
    assert len(provider.calls) == 1


def test_cache_expires_after_ttl():
    redis_client = FakeRedis()
    provider = FakeNewsProvider()

    cached_provider = CachedNewsProvider(
        provider,
        redis_client=redis_client,
        ttl_seconds=10,
    )

    first_result = cached_provider.search_articles("test claim", 5)

    redis_client.advance(11)

    second_result = cached_provider.search_articles("test claim", 5)

    assert first_result != second_result
    assert len(provider.calls) == 2


def test_cache_key_separates_different_result_counts():
    redis_client = FakeRedis()
    provider = FakeNewsProvider()

    cached_provider = CachedNewsProvider(
        provider,
        redis_client=redis_client,
    )

    cached_provider.search_articles("test claim", 5)
    cached_provider.search_articles("test claim", 3)

    assert len(provider.calls) == 2


def test_cache_key_separates_news_providers():
    redis_client = FakeRedis()

    first_provider = FakeNewsProvider()
    second_provider = AnotherFakeNewsProvider()

    cached_first = CachedNewsProvider(
        first_provider,
        redis_client=redis_client,
    )

    cached_second = CachedNewsProvider(
        second_provider,
        redis_client=redis_client,
    )

    cached_first.search_articles("test claim", 5)
    cached_second.search_articles("test claim", 5)

    assert len(first_provider.calls) == 1
    assert len(second_provider.calls) == 1


def test_redis_read_failure_does_not_break_provider():
    redis_client = FakeRedis()
    redis_client.fail_get = True

    provider = FakeNewsProvider()

    cached_provider = CachedNewsProvider(
        provider,
        redis_client=redis_client,
    )

    results = cached_provider.search_articles("test claim", 5)

    assert len(results) == 1
    assert len(provider.calls) == 1


def test_redis_write_failure_does_not_break_provider():
    redis_client = FakeRedis()
    redis_client.fail_setex = True

    provider = FakeNewsProvider()

    cached_provider = CachedNewsProvider(
        provider,
        redis_client=redis_client,
    )

    results = cached_provider.search_articles("test claim", 5)

    assert len(results) == 1
    assert len(provider.calls) == 1


def test_invalid_cached_json_is_removed_and_refetched():
    redis_client = FakeRedis()
    provider = FakeNewsProvider()

    cached_provider = CachedNewsProvider(
        provider,
        redis_client=redis_client,
    )

    key = cached_provider._cache_key("test claim", 5)
    redis_client.setex(key, 600, "invalid-json")

    results = cached_provider.search_articles("test claim", 5)

    assert len(results) == 1
    assert len(provider.calls) == 1
    assert json.loads(redis_client.get(key)) == results


def test_cache_rejects_non_positive_ttl():
    provider = FakeNewsProvider()

    try:
        CachedNewsProvider(
            provider,
            redis_client=FakeRedis(),
            ttl_seconds=0,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "TTL must be positive" in str(exc)