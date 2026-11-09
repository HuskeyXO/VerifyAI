
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app

import app.main as main


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db


def test_health_endpoint_returns_request_id():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

    request_id = response.headers.get("X-Request-ID")

    assert request_id is not None

    # Ensure the returned value is a valid UUID.
    UUID(request_id)


def test_each_request_receives_a_unique_request_id():
    with TestClient(app) as client:
        first = client.get("/")
        second = client.get("/health")

    first_id = first.headers.get("X-Request-ID")
    second_id = second.headers.get("X-Request-ID")

    assert first_id is not None
    assert second_id is not None
    assert first_id != second_id



def test_missing_verification_returns_request_id():
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
            response = client.get("/verifications/99999999")

        assert response.status_code == 404
        assert response.headers.get("X-Request-ID") is not None

    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()



def test_readiness_returns_200_when_dependencies_are_available(
    monkeypatch,
):
    monkeypatch.setattr(main, "check_database", lambda: None)
    monkeypatch.setattr(main, "check_redis", lambda: None)

    with TestClient(main.app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": "ok",
            "redis": "ok",
        },
    }


def test_readiness_returns_503_when_database_is_unavailable(
    monkeypatch,
):
    def unavailable_database():
        raise RuntimeError("Database unavailable")

    monkeypatch.setattr(
        main,
        "check_database",
        unavailable_database,
    )
    monkeypatch.setattr(main, "check_redis", lambda: None)

    with TestClient(main.app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "database": "unavailable",
            "redis": "ok",
        },
    }


def test_readiness_returns_503_when_redis_is_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(main, "check_database", lambda: None)

    def unavailable_redis():
        raise RuntimeError("Redis unavailable")

    monkeypatch.setattr(
        main,
        "check_redis",
        unavailable_redis,
    )

    with TestClient(main.app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "database": "ok",
            "redis": "unavailable",
        },
    }
