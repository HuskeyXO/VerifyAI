
from types import SimpleNamespace

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base

# Register all database models.
from app.models.article import Article
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.report import VerificationReport
from app.models.source import Source
from app.models.verification import VerificationRequest

import app.tasks.verification as verification_tasks

from app.services.verification_errors import (
    AIProviderUnavailableError,
)


@pytest.fixture
def test_db(monkeypatch):
    """Create an isolated SQLite database for worker tests."""

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

    monkeypatch.setattr(
        verification_tasks,
        "SessionLocal",
        TestingSessionLocal,
    )

    yield TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def create_queued_verification(session_factory):
    """Insert a verification request ready for processing."""

    with session_factory() as db:
        verification = VerificationRequest(
            claim="Test verification claim",
            status="queued",
        )

        db.add(verification)
        db.commit()
        db.refresh(verification)

        return verification.id


def get_status(session_factory, verification_id):
    with session_factory() as db:
        verification = (
            db.query(VerificationRequest)
            .filter(
                VerificationRequest.id == verification_id
            )
            .first()
        )

        return verification.status if verification else None


def test_worker_completes_verification(test_db, monkeypatch):
    verification_id = create_queued_verification(test_db)
    calls = []

    def fake_run_verification(verification_id, db):
        calls.append(verification_id)
        return SimpleNamespace(status="supported")

    monkeypatch.setattr(
        verification_tasks,
        "run_verification",
        fake_run_verification,
    )

    result = verification_tasks.run_verification_task.run(
        verification_id
    )

    assert result["status"] == "completed"
    assert result["report_status"] == "supported"
    assert get_status(test_db, verification_id) == "completed"
    assert calls == [verification_id]


def test_duplicate_task_does_not_run_completed_verification(
    test_db,
    monkeypatch,
):
    verification_id = create_queued_verification(test_db)
    calls = []

    def fake_run_verification(verification_id, db):
        calls.append(verification_id)
        return SimpleNamespace(status="supported")

    monkeypatch.setattr(
        verification_tasks,
        "run_verification",
        fake_run_verification,
    )

    first = verification_tasks.run_verification_task.run(
        verification_id
    )

    second = verification_tasks.run_verification_task.run(
        verification_id
    )

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert calls == [verification_id]


def test_transient_provider_error_schedules_retry(
    test_db,
    monkeypatch,
):
    verification_id = create_queued_verification(test_db)
    retry_details = {}

    def fake_run_verification(verification_id, db):
        try:
            raise RuntimeError("503 UNAVAILABLE")
        except RuntimeError as exc:
            raise AIProviderUnavailableError(
                "AI provider temporarily unavailable"
            ) from exc

    def fake_retry(*, exc=None, countdown=None):
        retry_details["exc"] = exc
        retry_details["countdown"] = countdown
        raise RuntimeError("Retry scheduled")

    monkeypatch.setattr(
        verification_tasks,
        "run_verification",
        fake_run_verification,
    )

    monkeypatch.setattr(
        verification_tasks.run_verification_task,
        "retry",
        fake_retry,
    )

    with pytest.raises(RuntimeError, match="Retry scheduled"):
        verification_tasks.run_verification_task.run(
            verification_id
        )

    assert retry_details["countdown"] == 5
    assert isinstance(
        retry_details["exc"],
        AIProviderUnavailableError,
    )

    assert get_status(test_db, verification_id) == "queued"


def test_permanent_provider_error_marks_job_failed(
    test_db,
    monkeypatch,
):
    verification_id = create_queued_verification(test_db)

    def fake_run_verification(verification_id, db):
        try:
            raise RuntimeError("400 INVALID_ARGUMENT")
        except RuntimeError as exc:
            raise AIProviderUnavailableError(
                "AI provider rejected the request"
            ) from exc

    monkeypatch.setattr(
        verification_tasks,
        "run_verification",
        fake_run_verification,
    )

    with pytest.raises(AIProviderUnavailableError):
        verification_tasks.run_verification_task.run(
            verification_id
        )

    assert get_status(test_db, verification_id) == "failed"


def test_transient_error_detection():
    assert verification_tasks.is_transient_provider_error(
        RuntimeError("503 UNAVAILABLE")
    )

    assert verification_tasks.is_transient_provider_error(
        RuntimeError("429 RESOURCE_EXHAUSTED")
    )

    assert not verification_tasks.is_transient_provider_error(
        RuntimeError("400 INVALID_ARGUMENT")
    )
