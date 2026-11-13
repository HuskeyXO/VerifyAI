from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArticleCreate(BaseModel):
    source_id: int = Field(gt=0)

    title: str = Field(
        min_length=1,
        max_length=500,
    )

    url: str = Field(
        min_length=8,
        max_length=1000,
    )

    author: str | None = Field(
        default=None,
        max_length=255,
    )

    content: str | None = Field(
        default=None,
        max_length=100000,
    )

    published_at: datetime | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or any(char.isspace() for char in value)
        ):
            raise ValueError("URL must be a valid HTTP or HTTPS URL")

        return value


class ArticleResponse(BaseModel):
    id: int
    source_id: int
    title: str
    url: str
    author: str | None
    content: str | None
    published_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)