
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.verification import VerificationRequest
from app.models.report import VerificationReport

from app.schemas.verification import (
    VerificationCreate,
    VerificationResponse,
)

from app.services.verification_pipeline import run_verification
from app.tasks.verification import run_verification_task


import logging

from app.core.logging_config import request_id_context

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/verifications",
    tags=["Verification"],
)


@router.post(
    "/",
    response_model=VerificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_verification(
    verification: VerificationCreate,
    db: Session = Depends(get_db),
):
    new_verification = VerificationRequest(
        claim=verification.claim
    )

    db.add(new_verification)
    db.commit()
    db.refresh(new_verification)

    return new_verification


@router.get(
    "/{verification_id}",
    response_model=VerificationResponse,
)
def get_verification(
    verification_id: int,
    db: Session = Depends(get_db),
):
    verification = (
        db.query(VerificationRequest)
        .filter(VerificationRequest.id == verification_id)
        .first()
    )

    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification request not found",
        )

    return verification


@router.post(
    "/{verification_id}/run",
    response_model=VerificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_verification_endpoint(
    verification_id: int,
    db: Session = Depends(get_db),
):
    verification = (
        db.query(VerificationRequest)
        .filter(VerificationRequest.id == verification_id)
        .with_for_update()
        .first()
    )

    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification request not found",
        )

    existing_report = (
        db.query(VerificationReport)
        .filter(
            VerificationReport.verification_id == verification_id
        )
        .first()
    )

    if existing_report is not None:
        if verification.status != "completed":
            verification.status = "completed"
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A report already exists for this verification",
        )

    if verification.status in {"queued", "processing"}:
        return verification

    if verification.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification has already been completed",
        )

    if verification.status not in {"pending", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification cannot be queued in its current state",
        )

    verification.status = "queued"
    db.commit()
    db.refresh(verification)

    try:
        request_id = request_id_context.get()

        task_result = run_verification_task.delay(
            verification_id,
            request_id,
        )

        logger.info(
            "Verification job submitted",
            extra={
                "verification_id": verification_id,
                "task_id": getattr(task_result, "id", None),
                "job_status": "queued",
            },
        )

    except Exception as exc:
        db.rollback()

        current = (
            db.query(VerificationRequest)
            .filter(VerificationRequest.id == verification_id)
            .first()
        )

        # Only mark failed if the worker has not already claimed it.
        if current is not None and current.status == "queued":
            current.status = "failed"
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not submit verification to the background queue",
        ) from exc

    db.refresh(verification)

    return verification
