from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.verification import VerificationRequest

from app.schemas.verification import VerificationCreate, VerificationResponse

from app.schemas.verification_report import VerificationReportResponse
from app.services.verification_pipeline import run_verification


from app.services.verification_errors import (
    VerificationNotFoundError,
    VerificationAlreadyRunError,
    NoNewsArticlesError,
    NewsProviderUnavailableError,
    AIProviderUnavailableError,
)


router = APIRouter(prefix="/verifications", tags=["Verification"])


@router.post("/", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)

def create_verification(verification: VerificationCreate, db: Session = Depends(get_db)):

    new_verification = VerificationRequest(claim = verification.claim) # this will get stored in database
    db.add(new_verification)
    db.commit()
    db.refresh(new_verification)

    return new_verification


@router.get("/{verification_id}", response_model=VerificationResponse)
def get_verification(verification_id: int, db: Session = Depends(get_db)):

    verification = ( db.query(VerificationRequest).filter(VerificationRequest.id == verification_id).first() )

    if verification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Verification request not found")

    return verification



@router.post(
    "/{verification_id}/run",
    response_model=VerificationReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_verification_endpoint(
    verification_id: int,
    db: Session = Depends(get_db),
):
    try:
        return run_verification(
            verification_id=verification_id,
            db=db,
        )

    except VerificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except VerificationAlreadyRunError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except NoNewsArticlesError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except (
        NewsProviderUnavailableError,
        AIProviderUnavailableError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
