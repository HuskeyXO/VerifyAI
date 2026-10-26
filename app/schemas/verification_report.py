from pydantic import BaseModel, ConfigDict

class VerificationReportResponse(BaseModel):
    id: int
    verification_id: int
    status: str
    confidence: float | None
    summary: str
    model_config=ConfigDict(
        from_attributes=True
    )
