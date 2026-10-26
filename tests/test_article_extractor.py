
import pytest

from app.services import article_extractor


def test_extracts_article_text(monkeypatch):
    article_text = "Apple published details about its products. " * 15

    monkeypatch.setattr(
        article_extractor,
        "fetch_url",
        lambda url: "<html>mock article</html>",
    )
    monkeypatch.setattr(
        article_extractor,
        "extract",
        lambda *args, **kwargs: article_text,
    )

    result = article_extractor.extract_article_text(
        "https://example.com/article"
    )

    assert result == " ".join(article_text.split())
    assert len(result) >= article_extractor.MIN_ARTICLE_CHARS


def test_blocked_or_unavailable_page_returns_none(monkeypatch):
    monkeypatch.setattr(
        article_extractor,
        "fetch_url",
        lambda url: None,
    )

    result = article_extractor.extract_article_text(
        "https://example.com/blocked"
    )

    assert result is None


def test_empty_extraction_returns_none(monkeypatch):
    monkeypatch.setattr(
        article_extractor,
        "fetch_url",
        lambda url: "<html></html>",
    )
    monkeypatch.setattr(
        article_extractor,
        "extract",
        lambda *args, **kwargs: None,
    )

    result = article_extractor.extract_article_text(
        "https://example.com/empty"
    )

    assert result is None


def test_short_extraction_returns_none(monkeypatch):
    monkeypatch.setattr(
        article_extractor,
        "fetch_url",
        lambda url: "<html>short page</html>",
    )
    monkeypatch.setattr(
        article_extractor,
        "extract",
        lambda *args, **kwargs: "This article is too short.",
    )

    result = article_extractor.extract_article_text(
        "https://example.com/short"
    )

    assert result is None
