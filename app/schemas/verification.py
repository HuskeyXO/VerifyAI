from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class VerificationCreate(BaseModel):
    claim: str = Field(min_length=10, max_length=1000)

    model_config = ConfigDict(str_strip_whitespace=True)


class VerificationResponse(BaseModel):
    id: int
    claim: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)