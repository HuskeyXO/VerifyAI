from app.core.logging_config import configure_logging
configure_logging()

from fastapi import FastAPI
from app.core.config import settings
from app.api.verification import router as verification_router
from app.api.source import router as source_router
from app.api.article import router as article_router
from app.api.claim import router as claim_router
from app.api.evidence import router as evidence_router
from app.api.report import router as report_router

from app.core.middleware import RequestLoggingMiddleware

import logging

from fastapi.responses import JSONResponse
from sqlalchemy import text
from redis import Redis


from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from slowapi.util import get_remote_address

from fastapi import FastAPI, Depends
from app.core.security import require_api_key


from app.core.rate_limit_middleware import RateLimitMiddleware

from app.core.database import engine

logger = logging.getLogger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    headers_enabled=True,
)



app = FastAPI(
    title=settings.app_name,
    version="1",
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

# SlowAPI checks requests before they reach the routes.
app.add_middleware(RateLimitMiddleware)

# Keep request logging outside rate limiting so 429 responses
# are also captured in your application logs.
app.add_middleware(RequestLoggingMiddleware)

protected_dependencies = [
    Depends(require_api_key)
]

app.include_router(
    verification_router,
    dependencies=protected_dependencies,
)

app.include_router(
    source_router,
    dependencies=protected_dependencies,
)

app.include_router(
    article_router,
    dependencies=protected_dependencies,
)

app.include_router(
    claim_router,
    dependencies=protected_dependencies,
)

app.include_router(
    evidence_router,
    dependencies=protected_dependencies,
)

app.include_router(
    report_router,
    dependencies=protected_dependencies,
)




@app.get("/")
def root():
    return {"message": "VerifyAI API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/ready")
def readiness_check():
    checks = {}

    try:
        check_database()
        checks["database"] = "ok"

    except Exception:
        checks["database"] = "unavailable"

        logger.exception(
            "Database readiness check failed"
        )

    try:
        check_redis()
        checks["redis"] = "ok"

    except Exception:
        checks["redis"] = "unavailable"

        logger.exception(
            "Redis readiness check failed"
        )

    ready = all(
        value == "ok"
        for value in checks.values()
    )

    result = {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }

    if not ready:
        return JSONResponse(
            status_code=503,
            content=result,
        )

    return result


def check_database() -> None:
    """Verify that PostgreSQL is reachable."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def check_redis() -> None:
    """Verify that Redis is reachable."""

    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )

    try:
        if not client.ping():
            raise RuntimeError("Redis ping failed")
    finally:
        client.close()
