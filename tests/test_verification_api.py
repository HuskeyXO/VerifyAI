from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.services.news.mock import MockNewsProvider

# Ensure all SQLAlchemy models are registered.
from app.models.article import Article
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.report import VerificationReport
from app.models.source import Source
from app.models.verification import VerificationRequest

import app.services.verification_pipeline as pipeline


def mock_analyze_claim(claim: str, articles: list[dict]) -> dict:
    """Return deterministic test evidence with valid article quotations."""
    evidence = []

    if len(articles) >= 1:
        evidence.append({
            "article_index": 1,
            "relation": "supports",
            "relevance_score": 0.7,
            "quoted_text": articles[0]["title"],
            "reason": "MOCK TEST: simulated supporting evidence.",
        })

    if len(articles) >= 2:
        evidence.append({
            "article_index": 2,
            "relation": "contradicts",
            "relevance_score": 0.7,
            "quoted_text": articles[1]["title"],
            "reason": "MOCK TEST: simulated contradicting evidence.",
        })

    return {"evidence": evidence}


def create_verification(client: TestClient) -> int:
    response = client.post(
        "/verifications/",
        json={
            "claim": "Apple increased the prices of selected products in India"
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def test_run_verification_creates_report(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        pipeline,
        "get_news_provider",
        lambda: MockNewsProvider(),
    )
    monkeypatch.setattr(
        pipeline,
        "analyze_claim",
        mock_analyze_claim,
    )

    monkeypatch.setattr(
        pipeline,
        "extract_article_text",
        lambda url: None,
    )

    try:
        with TestClient(app) as client:
            verification_id = create_verification(client)

            response = client.post(
                f"/verifications/{verification_id}/run"
            )

            assert response.status_code == 201

            report = response.json()
            assert report["verification_id"] == verification_id
            assert report["status"] == "uncertain"
            assert report["confidence"] == 0.5
            assert "2 evidence records" in report["summary"]
            assert "2 distinct sources" in report["summary"]

            # Confirm the report and evidence persisted in the test DB.
            with TestingSessionLocal() as db:
                saved_report = (
                    db.query(VerificationReport)
                    .filter(
                        VerificationReport.verification_id
                        == verification_id
                    )
                    .first()
                )

                saved_claims = (
                    db.query(Claim)
                    .filter(
                        Claim.verification_id == verification_id
                    )
                    .all()
                )

                assert saved_report is not None
                assert len(saved_claims) == 1

                saved_evidence = (
                    db.query(Evidence)
                    .filter(
                        Evidence.claim_id == saved_claims[0].id
                    )
                    .all()
                )

                assert len(saved_evidence) == 2


                saved_articles = db.query(Article).all()

                assert len(saved_articles) == 2
                assert all(article.content for article in saved_articles)
                assert any(
                    "TEST DATA:" in article.content
                    for article in saved_articles
                )

            saved_report_response = client.get(
            f"/verifications/{verification_id}/report"
        )

        assert saved_report_response.status_code == 200
        assert saved_report_response.json()["verification_id"] == verification_id

        evidence_response = client.get(
            f"/evidence/verification/{verification_id}"
        )

        assert evidence_response.status_code == 200

        evidence_items = evidence_response.json()

        assert len(evidence_items) == 2

        for item in evidence_items:
            assert item["excerpt"]
            assert item["article"]["title"]
            assert item["article"]["url"].startswith("https://")
            assert item["article"]["source"]["name"]
            assert item["article"]["source"]["domain"]

    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_duplicate_run_returns_409(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        pipeline,
        "get_news_provider",
        lambda: MockNewsProvider(),
    )
    monkeypatch.setattr(
        pipeline,
        "analyze_claim",
        mock_analyze_claim,
    )

    monkeypatch.setattr(
        pipeline,
        "extract_article_text",
        lambda url: None,
)

    try:
        with TestClient(app) as client:
            verification_id = create_verification(client)
            url = f"/verifications/{verification_id}/run"

            first = client.post(url)
            second = client.post(url)

            assert first.status_code == 201
            assert second.status_code == 409

    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_missing_verification_returns_404():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/verifications/99999999/run"
            )

            assert response.status_code == 404

    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
