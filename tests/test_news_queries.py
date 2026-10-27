
from app.services.verification_pipeline import build_news_queries


def test_logitech_query_preserves_company_and_product():
    queries = build_news_queries(
        "Logitech sells gaming mice in India"
    )

    assert queries
    assert all("Logitech" in query for query in queries)
    assert all("sells" not in query.lower() for query in queries)
    assert any("gaming mice" in query.lower() for query in queries)
    assert any("gaming mouse" in query.lower() for query in queries)


def test_subjective_gaming_mouse_claim_preserves_logitech():
    queries = build_news_queries(
        "Best gaming mouse in India comes from Logitech"
    )

    assert queries
    assert all("Logitech" in query for query in queries)
    assert any("gaming mouse" in query.lower() for query in queries)


def test_rbi_claim_has_specialized_query():
    queries = build_news_queries(
        "The Reserve Bank of India changed its repo rate"
    )

    assert any("RBI" in query and "repo rate" in query for query in queries)
