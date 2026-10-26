
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.article import Article
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.source import Source
from app.models.verification import VerificationRequest
from app.services.evidence import save_evidence


def create_test_records():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    db = TestingSession()

    verification = VerificationRequest(
        claim="Apple raised iPhone prices in India"
    )
    source = Source(
        name="Example News",
        domain="example.com",
    )

    db.add_all([verification, source])
    db.flush()

    claim = Claim(
        verification_id=verification.id,
        claim_text=verification.claim,
    )

    article = Article(
        source_id=source.id,
        title="Apple raises iPhone prices in India",
        url="https://example.com/apple-prices",
        content="The report discusses changes to iPhone prices.",
    )

    db.add_all([claim, article])
    db.flush()

    return engine, db, claim, article


def test_save_evidence_accepts_exact_title_quote():
    engine, db, claim, article = create_test_records()

    try:
        quote = article.title

        saved = save_evidence(
            claim=claim,
            articles=[article],
            ai_evidence=[{
                "article_index": 1,
                "relation": "supports",
                "relevance_score": 0.9,
                "quoted_text": quote,
                "reason": "The title mentions a price increase.",
            }],
            db=db,
        )

        assert len(saved) == 1
        assert saved[0].excerpt == quote
        assert saved[0].supports_claim is True

    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_save_evidence_rejects_invented_quote():
    engine, db, claim, article = create_test_records()

    try:
        saved = save_evidence(
            claim=claim,
            articles=[article],
            ai_evidence=[{
                "article_index": 1,
                "relation": "supports",
                "relevance_score": 0.9,
                "quoted_text": (
                    "Apple officially increased every product price by 41%."
                ),
                "reason": "Intentionally invented quotation.",
            }],
            db=db,
        )

        assert saved == []
        assert db.query(Evidence).count() == 0

    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_irrelevant_evidence_is_not_saved():
    engine, db, claim, article = create_test_records()

    try:
        saved = save_evidence(
            claim=claim,
            articles=[article],
            ai_evidence=[{
                "article_index": 1,
                "relation": "irrelevant",
                "relevance_score": 0.9,
                "quoted_text": article.title,
                "reason": "This article is contextual commentary.",
            }],
            db=db,
        )

        assert saved == []
        assert db.query(Evidence).count() == 0

    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
