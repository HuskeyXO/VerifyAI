from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ArticleCreate(BaseModel):
    source_id: int
    title: str
    url: str
    author: str | None = None
    content: str | None = None
    published_at: datetime | None = None


class ArticleResponse(BaseModel):
    id: int
    source_id: int
    title: str
    url: str
    author: str | None
    content: str | None
    published_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
