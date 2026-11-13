import pytest
from pydantic import ValidationError

from app.schemas.article import ArticleCreate
from app.schemas.claim import ClaimCreate
from app.schemas.evidence import EvidenceCreate
from app.schemas.source import SourceCreate
from app.schemas.verification import VerificationCreate


# Verification

def test_verification_create_accepts_valid_claim():
    payload = VerificationCreate(
        claim="   Apple increased prices of selected products in India.   "
    )

    assert payload.claim == "Apple increased prices of selected products in India."


@pytest.mark.parametrize("claim", ["short", "x" * 1001, " " * 10])
def test_verification_create_rejects_invalid_claim(claim):
    with pytest.raises(ValidationError):
        VerificationCreate(claim=claim)


# Claim

def test_claim_create_accepts_valid_payload():
    payload = ClaimCreate(
        verification_id=1,
        claim_text="A sufficiently long claim for verification.",
    )

    assert payload.verification_id == 1


@pytest.mark.parametrize("verification_id", [0, -1])
def test_claim_create_rejects_invalid_verification_id(verification_id):
    with pytest.raises(ValidationError):
        ClaimCreate(
            verification_id=verification_id,
            claim_text="A sufficiently long claim for verification.",
        )


# Article

@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/article",
        "http://example.com/article",
    ],
)
def test_article_create_accepts_valid_http_urls(url):
    payload = ArticleCreate(
        source_id=1,
        title="Example article",
        url=url,
    )

    assert payload.url == url


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "ftp://example.com/article",
        "javascript:alert(1)",
        "http://",
    ],
)
def test_article_create_rejects_invalid_urls(url):
    with pytest.raises(ValidationError):
        ArticleCreate(
            source_id=1,
            title="Example article",
            url=url,
        )


def test_article_create_rejects_invalid_source_id():
    with pytest.raises(ValidationError):
        ArticleCreate(
            source_id=0,
            title="Example article",
            url="https://example.com/article",
        )


def test_article_create_rejects_oversized_title():
    with pytest.raises(ValidationError):
        ArticleCreate(
            source_id=1,
            title="x" * 501,
            url="https://example.com/article",
        )


def test_article_create_rejects_oversized_author():
    with pytest.raises(ValidationError):
        ArticleCreate(
            source_id=1,
            title="Example article",
            url="https://example.com/article",
            author="x" * 256,
        )


def test_article_create_rejects_oversized_content():
    with pytest.raises(ValidationError):
        ArticleCreate(
            source_id=1,
            title="Example article",
            url="https://example.com/article",
            content="x" * 100001,
        )


# Evidence

def test_evidence_create_accepts_valid_payload():
    payload = EvidenceCreate(
        claim_id=1,
        article_id=1,
        excerpt="This is a sufficiently long evidence excerpt.",
        supports_claim=True,
        relevance_score=0.85,
    )

    assert payload.relevance_score == 0.85


@pytest.mark.parametrize("score", [-0.01, 1.01, float("nan"), float("inf"), -float("inf")])
def test_evidence_create_rejects_invalid_relevance_score(score):
    with pytest.raises(ValidationError):
        EvidenceCreate(
            claim_id=1,
            article_id=1,
            excerpt="This is a sufficiently long evidence excerpt.",
            supports_claim=True,
            relevance_score=score,
        )


@pytest.mark.parametrize("field,value", [
    ("claim_id", 0),
    ("claim_id", -1),
    ("article_id", 0),
    ("article_id", -1),
])
def test_evidence_create_rejects_invalid_foreign_keys(field, value):
    payload = {
        "claim_id": 1,
        "article_id": 1,
        "excerpt": "This is a sufficiently long evidence excerpt.",
        "supports_claim": True,
        "relevance_score": 0.5,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        EvidenceCreate(**payload)


def test_evidence_create_rejects_oversized_excerpt():
    with pytest.raises(ValidationError):
        EvidenceCreate(
            claim_id=1,
            article_id=1,
            excerpt="x" * 10001,
            supports_claim=True,
        )


# Source

def test_source_create_accepts_valid_payload():
    payload = SourceCreate(
        name="  Example News  ",
        domain="  example.com  ",
        source_type="news",
    )

    assert payload.name == "Example News"
    assert payload.domain == "example.com"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "A", "domain": "example.com"},
        {"name": "Example News", "domain": "ab"},
        {"name": "x" * 256, "domain": "example.com"},
        {"name": "Example News", "domain": "x" * 256},
        {"name": "Example News", "domain": "example.com", "source_type": "x" * 51},
        {"name": "Example News", "domain": "example.com", "source_type": ""},
    ],
)
def test_source_create_rejects_invalid_payload(payload):
    with pytest.raises(ValidationError):
        SourceCreate(**payload)