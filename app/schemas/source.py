from pydantic import BaseModel, Field, ConfigDict


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    domain: str = Field(min_length=3, max_length=255)
    source_type: str = Field(default="news", min_length=1, max_length=50)

    model_config = ConfigDict(str_strip_whitespace=True)


class SourceResponse(BaseModel):
    id: int
    name: str
    domain: str
    source_type: str

    model_config = ConfigDict(from_attributes=True)