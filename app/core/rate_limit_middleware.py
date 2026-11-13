from fastapi import Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/", "/health", "/ready"}

    async def dispatch(self, request: Request, call_next) -> Response:
        limiter = request.app.state.limiter

        # Keep public operational endpoints accessible.
        if not limiter.enabled or request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        try:
            # Pass no endpoint function. SlowAPI then uses the request URL
            # as its key, avoiding FastAPI's lazy router discovery.
            limiter._check_request_limit(
                request,
                endpoint_func=None,
                in_middleware=True,
            )

        except RateLimitExceeded as exc:
            return _rate_limit_exceeded_handler(request, exc)

        response = await call_next(request)

        # Preserve the configured rate-limit response headers.
        if limiter._headers_enabled:
            response = limiter._inject_headers(
                response,
                request.state.view_rate_limit,
            )

        return response