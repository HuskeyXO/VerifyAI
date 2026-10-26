from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utc_now_naive

class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    verification_id: Mapped[int] = mapped_column(
        ForeignKey("verification_requests.id"),
        nullable=False
    )

    claim_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="unverified",
        nullable=False
    )

    confidence: Mapped[float | None] = mapped_column(
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        nullable=False
    )

    verification = relationship(
        "VerificationRequest",
        back_populates="claims"
    )
