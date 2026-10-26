from fastapi import FastAPI

from app.core.config import settings
from app.api.verification import router as verification_router
from app.api.source import router as source_router
from app.api.article import router as article_router
from app.api.claim import router as claim_router
from app.api.evidence import router as evidence_router
from app.api.report import router as report_router





app = FastAPI(
    title = settings.app_name,
    version = "1"
)

app.include_router(verification_router)
app.include_router(source_router)
app.include_router(article_router)
app.include_router(claim_router)
app.include_router(evidence_router)
app.include_router(report_router)





@app.get("/")
def root():
    return {"message": "VerifyAI API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
