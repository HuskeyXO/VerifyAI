from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class EvidenceCreate(BaseModel):
    claim_id: int = Field(gt=0)
    article_id: int = Field(gt=0)

    excerpt: str = Field(
        min_length=10,
        max_length=10000,
    )

    supports_claim: bool

    relevance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class EvidenceResponse(BaseModel):
    id: int
    claim_id: int
    article_id: int
    excerpt: str
    supports_claim: bool
    relevance_score: float | None

    model_config = ConfigDict(from_attributes=True)


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