
from urllib.parse import urlparse

from trafilatura import fetch_url, extract


MAX_ARTICLE_CHARS = 20_000
MIN_ARTICLE_CHARS = 300


def extract_article_text(url: str) -> str | None:
    """
    Try to extract the main text from a public article page.

    Return None when download or extraction fails so the caller
    can fall back to the text supplied by the news provider.
    """
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None

    try:
        downloaded = fetch_url(url)

        if not downloaded:
            return None

        article_text = extract(
            downloaded,
            url=url,
            include_comments=False,
            include_tables=False,
        )

        if not article_text:
            return None

        article_text = " ".join(article_text.split())

        if len(article_text) < MIN_ARTICLE_CHARS:
            return None

        return article_text[:MAX_ARTICLE_CHARS]

    except Exception:
        # Extraction is best-effort. The pipeline can use GNews text
        # if the publisher blocks access or its page cannot be parsed.
        return None
