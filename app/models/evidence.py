from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utc_now_naive

class Evidence(Base):

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), nullable=False)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    supports_claim: Mapped[bool] = mapped_column(Boolean, nullable=False)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)


    claim = relationship("Claim")
    article = relationship("Article")
