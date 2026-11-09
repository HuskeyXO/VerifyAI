
import logging
from app.core.celery_app import celery_app
from app.core.database import SessionLocal

from app.models.verification import VerificationRequest
from app.models.report import VerificationReport

from app.services.verification_pipeline import run_verification

from app.services.verification_errors import (
    AIProviderUnavailableError,
    NewsProviderUnavailableError,
)

from app.core.logging_config import request_id_context


logger = logging.getLogger(__name__)



def is_transient_provider_error(exc: Exception) -> bool:
    """Check whether the underlying provider error is temporary."""

    transient_markers = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "UNAVAILABLE",
        "RESOURCE_EXHAUSTED",
        "DEADLINE_EXCEEDED",
        "TIMEOUT",
        "CONNECTION",
    )

    current = exc
    visited = set()

    while current is not None and id(current) not in visited:
        visited.add(id(current))

        message = str(current).upper()

        if any(marker in message for marker in transient_markers):
            return True

        current = current.__cause__ or current.__context__

    return False


@celery_app.task(
    bind=True,
    name="app.tasks.verification.run_verification_task",
    max_retries=3,
)
def run_verification_task(
    self,
    verification_id: int,
    request_id: str | None = None,
) -> dict:
    """
    Execute a verification request in a background worker.

    The worker creates and closes its own database session.
    """

    request_token = request_id_context.set(request_id or "-")
    db = None

    try:
        db = SessionLocal()
        verification = (
            db.query(VerificationRequest)
            .filter(VerificationRequest.id == verification_id)
            .with_for_update()
            .first()
        )


        if verification is None:
                raise RuntimeError(
                    f"Verification {verification_id} disappeared during retry"
                )

        # Only process jobs that have actually been queued.
        if verification.status != "queued":
            return {
                "verification_id": verification_id,
                "status": verification.status,
            }

        # Recover if a report was committed before a previous
        # worker execution could update the job status.
        existing_report = (
            db.query(VerificationReport)
            .filter(
                VerificationReport.verification_id == verification_id
            )
            .first()
        )

        if existing_report is not None:
            verification.status = "completed"
            db.commit()

            return {
                "verification_id": verification_id,
                "status": "completed",
                "report_status": existing_report.status,
            }

        verification.status = "processing"
        db.commit()

        logger.info(
            "Starting verification",
            extra={
                "verification_id": verification_id,
                "task_id": self.request.id,
                "job_status": "processing",
            },
        )

        report = run_verification(
            verification_id=verification_id,
            db=db,
        )

        # The pipeline commits the report. Update the job status
        # separately from the report verdict.
        verification = (
            db.query(VerificationRequest)
            .filter(VerificationRequest.id == verification_id)
            .first()
        )

        if verification is not None:
            verification.status = "completed"
            db.commit()

        logger.info(
            "Verification completed",
            extra={
                "verification_id": verification_id,
                "task_id": self.request.id,
                "verdict": report.status,
                "job_status": "completed",
            },
        )

        return {
            "verification_id": verification_id,
            "status": "completed",
            "report_status": report.status,
        }

    except (
        AIProviderUnavailableError,
        NewsProviderUnavailableError,
    ) as exc:
        db.rollback()

        if (
            is_transient_provider_error(exc)
            and self.request.retries < self.max_retries
        ):
            verification = (
                db.query(VerificationRequest)
                .filter(
                    VerificationRequest.id == verification_id
                )
                .with_for_update()
                .first()
            )

            existing_report = (
                db.query(VerificationReport)
                .filter(
                    VerificationReport.verification_id
                    == verification_id
                )
                .first()
            )

            if existing_report is not None:
                verification.status = "completed"
                db.commit()

                return {
                    "verification_id": verification_id,
                    "status": "completed",
                    "report_status": existing_report.status,
                }

            if verification is not None:
                verification.status = "queued"
                db.commit()

            countdown = min(
                60,
                5 * (2 ** self.request.retries),
            )

            logger.warning(
                "Transient provider failure for verification %s. "
                "Retrying in %s seconds. Retry %s/%s.",
                verification_id,
                countdown,
                self.request.retries + 1,
                self.max_retries,
            )

            extra={
                "verification_id": verification_id,
                "task_id": self.request.id,
                "retry_count": self.request.retries + 1,
                "retry_delay": countdown,
            }

            raise self.retry(
                exc=exc,
                countdown=countdown,
            )

        db.rollback()

        try:
            verification = (
                db.query(VerificationRequest)
                .filter(
                    VerificationRequest.id == verification_id
                )
                .first()
            )

            if verification is not None:
                verification.status = "failed"
                db.commit()

        except Exception:
            db.rollback()
            logger.exception(
                "Could not save failure status for verification %s",
                verification_id,
            )

        logger.exception(
            "Verification %s failed after provider error",
            verification_id,
        )

        raise

    except Exception:
        db.rollback()

        try:
            verification = (
                db.query(VerificationRequest)
                .filter(
                    VerificationRequest.id == verification_id
                )
                .first()
            )

            if verification is not None:
                verification.status = "failed"
                db.commit()

        except Exception:
            db.rollback()
            logger.exception(
                "Could not save failure status for verification %s",
                verification_id,
            )

        logger.exception(
            "Verification %s failed",
            verification_id,
        )

        raise

    finally:
        try:
            if db is not None:
                db.close()
        finally:
            request_id_context.reset(request_token)
