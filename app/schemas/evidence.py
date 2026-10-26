from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class EvidenceCreate(BaseModel):
    claim_id: int
    article_id: int
    excerpt: str = Field(min_length=10)
    supports_claim: bool
    relevance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0
    )


class EvidenceResponse(BaseModel):
    id: int
    claim_id: int
    article_id: int
    excerpt: str
    supports_claim: bool
    relevance_score: float | None

    model_config=ConfigDict(
        from_attributes=True
    )



class EvidenceSourceResponse(BaseModel):
    name: str
    domain: str

    model_config = ConfigDict(from_attributes=True)


class EvidenceArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    published_at: datetime | None
    source: EvidenceSourceResponse

    model_config = ConfigDict(from_attributes=True)


class EvidenceDetailResponse(BaseModel):
    id: int
    claim_id: int
    article_id: int
    excerpt: str
    supports_claim: bool
    relevance_score: float | None
    article: EvidenceArticleResponse

    model_config = ConfigDict(from_attributes=True)
