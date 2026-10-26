from fastapi import HTTPException, status, Depends, APIRouter
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.verification import VerificationRequest
from app.models.report import VerificationReport

from app.schemas.verification_report import VerificationReportResponse

from app.services.verification_report import generate_verification_result

router = APIRouter(
    prefix="/verifications",
    tags=["Verification"]
)

@router.post("/{verification_id}/report", response_model=VerificationReportResponse, status_code=status.HTTP_201_CREATED)
def create_verification_report(verification_id: int, db: Session = Depends(get_db)):

    verification = ( db.query(VerificationRequest).filter(VerificationRequest.id == verification_id).first() )

    if verification is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail="Verification request not found"
        )

    existing_report = ( db.query(VerificationReport).filter(VerificationReport.verification_id == verification_id).first() )

    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification report already exist"
        )

    result = generate_verification_result(verification_id, db)

    report = VerificationReport(
        verification_id = verification_id,
        status = result["status"],
        confidence = result["confidence"],
        summary = result["summary"]
    )


    db.add(report)
    verification.status = result["status"]

    db.commit()
    db.refresh(report)

    return report



@router.get(
    "/{verification_id}/report",
    response_model=VerificationReportResponse,
)
def get_verification_report(
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

    report = (
        db.query(VerificationReport)
        .filter(
            VerificationReport.verification_id == verification_id
        )
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification report not found",
        )

    return report
