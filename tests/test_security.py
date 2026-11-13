
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, limiter
from app.core.config import settings
from app.core.database import Base, get_db

# Register database models.
from app.models.article import Article
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.report import VerificationReport
from app.models.source import Source
from app.models.verification import VerificationRequest


TEST_API_KEY = "test-api-key"


@pytest.fixture
def security_client(monkeypatch):
    """Provide an authenticated test client with an isolated database."""

    monkeypatch.setattr(settings, "api_key", TEST_API_KEY)

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
            yield client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_protected_endpoint_rejects_missing_api_key(
    security_client,
):
    response = security_client.get("/verifications/99999999")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_protected_endpoint_rejects_invalid_api_key(
    security_client,
):
    response = security_client.get(
        "/verifications/99999999",
        headers={"X-API-Key": "incorrect-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_protected_endpoint_accepts_valid_api_key(
    security_client,
):
    response = security_client.get(
        "/verifications/99999999",
        headers={"X-API-Key": TEST_API_KEY},
    )

    # Authentication succeeds. The requested verification does not exist.
    assert response.status_code == 404
    assert response.json()["detail"] == "Verification request not found"


def test_authentication_fails_closed_when_api_key_is_unconfigured(
    security_client,
    monkeypatch,
):
    monkeypatch.setattr(settings, "api_key", "")

    response = security_client.get(
        "/verifications/99999999",
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "API authentication is not configured"


def test_public_health_endpoint_does_not_require_api_key(
    security_client,
):
    response = security_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_protected_endpoint_is_rate_limited(security_client):
    limiter.reset()

    headers = {"X-API-Key": TEST_API_KEY}

    try:
        # The first 60 requests should be allowed.
        for _ in range(60):
            response = security_client.get(
                "/verifications/99999999",
                headers=headers,
            )
            assert response.status_code == 404

        # The 61st request should be rejected.
        response = security_client.get(
            "/verifications/99999999",
            headers=headers,
        )

        assert response.status_code == 429

        # Public health endpoint should remain accessible.
        health_response = security_client.get("/health")
        assert health_response.status_code == 200

    finally:
        limiter.reset()
