from pydantic import BaseModel, Field

class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    domain: str = Field(min_length=3, max_length=255)
    source_type: str = "news"

class SourceResponse(BaseModel):
    id: int
    name: str
    domain: str
    source_type: str
    model_config = {
        "from_attributes": True
    }
