from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.claim import Claim
from app.models.verification import VerificationRequest
from app.schemas.claim import ClaimCreate, ClaimResponse

router = APIRouter(
    prefix="/claims",
    tags=["Claims"]
)

@router.post("/", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def create_claim(claim: ClaimCreate, db: Session = Depends(get_db)):

    verification = ( db.query(VerificationRequest).filter(VerificationRequest.id == claim.verification_id).first() )

    if verification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="verification request not found")

    new_claim = Claim(
        verification_id = claim.verification_id,
        claim_text = claim.claim_text
    )

    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)

    return new_claim
