from datetime import datetime
from pydantic import BaseModel, ConfigDict

class VerificationCreate(BaseModel):
    claim: str

class VerificationResponse(BaseModel):
    id: int
    claim: str
    status: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
