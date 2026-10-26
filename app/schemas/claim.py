from pydantic import BaseModel, Field, ConfigDict

class ClaimCreate(BaseModel):

    verification_id: int
    claim_text: str = Field(min_length=10, max_length=1000)

class ClaimResponse(BaseModel):
    id: int
    verification_id: int
    claim_text: str
    status: str
    confidence: float | None

    model_config = ConfigDict(
        from_attributes=True
    )
