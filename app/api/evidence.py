from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.evidence import Evidence
from app.models.claim import Claim
from app.models.article import Article
from app.models.verification import VerificationRequest

from app.schemas.evidence import (
    EvidenceCreate,
    EvidenceResponse,
    EvidenceDetailResponse,
)
from app.services.evidence import MIN_RELEVANCE_SCORE

router = APIRouter(
    prefix="/evidence",
    tags=["Evidence"]
)

@router.post("/", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_evidence(evidence: EvidenceCreate, db: Session = Depends(get_db)):
    claim = ( db.query(Claim).filter(Claim.id == evidence.claim_id).first() )
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="article not found"
        )


    article = ( db.query(Article).filter(Article.id == evidence.article_id).first() )
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="article not found"
        )


    def normalize_text(text: str) -> str:
        return " ".join(text.split())


    article_text = normalize_text(
        f"{article.title}\n{article.content or ''}"
    )

    if normalize_text(evidence.excerpt) not in article_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Evidence excerpt must match the article title or stored text",
        )

    if (
        evidence.relevance_score is not None
        and evidence.relevance_score < MIN_RELEVANCE_SCORE
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Evidence relevance score must be at least {MIN_RELEVANCE_SCORE}",
        )


    new_evidence = Evidence(
        claim_id = evidence.claim_id,
        article_id = evidence.article_id,
        excerpt = evidence.excerpt,
        supports_claim = evidence.supports_claim,
        relevance_score = evidence.relevance_score
    )

    db.add(new_evidence)
    db.commit()
    db.refresh(new_evidence)

    return new_evidence



@router.get(
    "/verification/{verification_id}",
    response_model=list[EvidenceDetailResponse],
)
def get_evidence_for_verification(
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

    evidence_items = (
        db.query(Evidence)
        .join(Claim, Evidence.claim_id == Claim.id)
        .options(
            joinedload(Evidence.article).joinedload(Article.source)
        )
        .filter(Claim.verification_id == verification_id)
        .order_by(Evidence.id)
        .all()
    )

    return evidence_items
