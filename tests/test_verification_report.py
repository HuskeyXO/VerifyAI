
from app.models.article import Article
from app.models.evidence import Evidence
from app.models.source import Source
from app.services.verification_report import _evaluate_evidence

def make_evidence(
    evidence_id: int,
    article_id: int,
    source_domain: str,
    supports_claim: bool,
    relevance_score: float,
) -> Evidence:
    source = Source(
        id=article_id,
        name=source_domain,
        domain=source_domain,
    )

    article = Article(
        id=article_id,
        source_id=article_id,
        title=f"Test article {article_id}",
        url=f"https://{source_domain}/article-{article_id}",
        content="Test article content",
    )
    article.source = source

    evidence = Evidence(
        id=evidence_id,
        claim_id=1,
        article_id=article_id,
        excerpt="Test evidence",
        supports_claim=supports_claim,
        relevance_score=relevance_score,
    )
    evidence.article = article

    return evidence


def test_single_source_produces_uncertain_verdict():
    evidence = [
        make_evidence(
            evidence_id=1,
            article_id=101,
            source_domain="news-one.example",
            supports_claim=True,
            relevance_score=0.95,
        )
    ]

    result = _evaluate_evidence(evidence)

    assert result["status"] == "uncertain"
    assert result["confidence"] is None
    assert result["source_count"] == 1


def test_multiple_articles_from_one_publisher_count_as_one_source():
    evidence = [
        make_evidence(
            evidence_id=1,
            article_id=101,
            source_domain="news-one.example",
            supports_claim=True,
            relevance_score=0.95,
        ),
        make_evidence(
            evidence_id=2,
            article_id=102,
            source_domain="news-one.example",
            supports_claim=True,
            relevance_score=0.85,
        ),
    ]

    result = _evaluate_evidence(evidence)

    assert result["status"] == "uncertain"
    assert result["source_count"] == 1
    assert result["article_count"] == 2
    assert result["evidence_count"] == 2


def test_two_independent_supporting_sources_can_support_claim():
    evidence = [
        make_evidence(
            evidence_id=1,
            article_id=101,
            source_domain="news-one.example",
            supports_claim=True,
            relevance_score=0.90,
        ),
        make_evidence(
            evidence_id=2,
            article_id=102,
            source_domain="news-two.example",
            supports_claim=True,
            relevance_score=0.80,
        ),
    ]

    result = _evaluate_evidence(evidence)

    assert result["status"] == "supported"
    assert result["source_count"] == 2
    assert result["confidence"] is not None
    assert 0.5 < result["confidence"] < 1.0



def test_two_independent_contradicting_sources_can_contradict_claim():
    evidence = [
        make_evidence(
            evidence_id=1,
            article_id=101,
            source_domain="news-one.example",
            supports_claim=False,
            relevance_score=0.90,
        ),
        make_evidence(
            evidence_id=2,
            article_id=102,
            source_domain="news-two.example",
            supports_claim=False,
            relevance_score=0.80,
        ),
    ]

    result = _evaluate_evidence(evidence)

    assert result["status"] == "contradicted"
    assert result["source_count"] == 2
    assert result["confidence"] is not None
    assert 0.5 < result["confidence"] < 1.0


def test_balanced_evidence_from_two_sources_remains_uncertain():
    evidence = [
        make_evidence(
            evidence_id=1,
            article_id=101,
            source_domain="news-one.example",
            supports_claim=True,
            relevance_score=0.80,
        ),
        make_evidence(
            evidence_id=2,
            article_id=102,
            source_domain="news-two.example",
            supports_claim=False,
            relevance_score=0.80,
        ),
    ]

    result = _evaluate_evidence(evidence)

    assert result["status"] == "uncertain"
    assert result["confidence"] == 0.5
    assert result["source_count"] == 2



def test_low_relevance_evidence_is_ignored():
    evidence = [
        make_evidence(
            evidence_id=1,
            article_id=101,
            source_domain="news-one.example",
            supports_claim=True,
            relevance_score=0.4,
        ),
        make_evidence(
            evidence_id=2,
            article_id=102,
            source_domain="news-two.example",
            supports_claim=False,
            relevance_score=0.5,
        ),
    ]

    result = _evaluate_evidence(evidence)

    assert result["status"] == "uncertain"
    assert result["confidence"] is None
    assert result["evidence_count"] == 0
    assert result["source_count"] == 0



def test_same_story_from_two_publishers_remains_uncertain():
    first = make_evidence(
        evidence_id=1,
        article_id=101,
        source_domain="news-one.example",
        supports_claim=True,
        relevance_score=0.95,
    )

    second = make_evidence(
        evidence_id=2,
        article_id=102,
        source_domain="news-two.example",
        supports_claim=True,
        relevance_score=0.90,
    )

    # Different publishers, but the exact same headline.
    second.article.title = first.article.title

    result = _evaluate_evidence([first, second])

    assert result["source_count"] == 2
    assert result["article_count"] == 2
    assert result["independent_story_count"] == 1
    assert result["status"] == "uncertain"
    assert result["confidence"] is None



def test_near_duplicate_headlines_count_as_one_story():
    first = make_evidence(
        evidence_id=1,
        article_id=101,
        source_domain="news-one.example",
        supports_claim=True,
        relevance_score=0.95,
    )

    second = make_evidence(
        evidence_id=2,
        article_id=102,
        source_domain="news-two.example",
        supports_claim=True,
        relevance_score=0.90,
    )

    first.article.title = (
        "Apple raises iPhone prices in India: new rates announced"
    )
    second.article.title = (
        "Apple raises iPhone prices in India: new rates announced today"
    )

    result = _evaluate_evidence([first, second])

    assert result["source_count"] == 2
    assert result["article_count"] == 2
    assert result["independent_story_count"] == 1
    assert result["status"] == "uncertain"
    assert result["confidence"] is None




def test_same_article_content_with_different_headlines_is_one_story():
    shared_content = (
        "Apple announced changes to prices for selected products in India. "
        "The report describes the affected devices, retail pricing, and "
        "the company's pricing changes in the Indian market. "
    ) * 4

    first = make_evidence(
        evidence_id=1,
        article_id=101,
        source_domain="news-one.example",
        supports_claim=True,
        relevance_score=0.95,
    )

    second = make_evidence(
        evidence_id=2,
        article_id=102,
        source_domain="news-two.example",
        supports_claim=True,
        relevance_score=0.90,
    )

    first.article.title = "Apple changes prices for selected Indian products"
    second.article.title = "New Apple pricing announced across India"

    first.article.content = shared_content
    second.article.content = shared_content

    result = _evaluate_evidence([first, second])

    assert result["source_count"] == 2
    assert result["article_count"] == 2
    assert result["independent_story_count"] == 1
    assert result["status"] == "uncertain"
    assert result["confidence"] is None



def test_different_stories_about_same_company_stay_separate():
    first = make_evidence(
        evidence_id=1,
        article_id=101,
        source_domain="news-one.example",
        supports_claim=True,
        relevance_score=0.9,
    )

    second = make_evidence(
        evidence_id=2,
        article_id=102,
        source_domain="news-two.example",
        supports_claim=True,
        relevance_score=0.85,
    )

    first.article.title = "Apple opens a new retail store in Delhi"
    first.article.content = (
        "Apple opened a new retail store in Delhi. The location offers "
        "product demonstrations, technical support, and device trade-ins "
        "for customers visiting the capital."
    )

    second.article.title = "Apple updates official iPhone prices in India"
    second.article.content = (
        "Apple updated the official retail prices of selected iPhone "
        "models in India. The report lists revised device prices and "
        "compares them with the previous prices."
    )

    result = _evaluate_evidence([first, second])

    assert result["source_count"] == 2
    assert result["article_count"] == 2
    assert result["independent_story_count"] == 2
    assert result["status"] == "supported"
