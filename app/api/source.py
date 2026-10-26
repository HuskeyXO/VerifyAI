from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceResponse

router = APIRouter(
    prefix="/sources",
    tags=["Sources"]
)

@router.post("/", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(source: SourceCreate, db: Session = Depends(get_db)):

    new_source = Source(
        name=source.name,
        domain=source.domain,
        source_type=source.source_type
    )

    db.add(new_source)
    db.commit()
    db.refresh(new_source)

    return new_source
