
import logging
import time
import uuid

from app.core.logging_config import request_id_context


logger = logging.getLogger("verifyai.http")


class RequestLoggingMiddleware:
    """Log HTTP requests and attach a unique request ID."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        token = request_id_context.set(request_id)

        start_time = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message):
            nonlocal status_code, response_started

            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_started = True

                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-request-id", request_id.encode("ascii"))
                )

                message = {
                    **message,
                    "headers": headers,
                }

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_with_request_id,
            )

        except Exception:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "HTTP request failed",
                extra={
                    "http_method": scope["method"],
                    "http_path": scope["path"],
                    "http_status_code": (
                        status_code if response_started else 500
                    ),
                    "duration_ms": duration_ms,
                },
            )
            raise

        else:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )

            logger.info(
                "HTTP request completed",
                extra={
                    "http_method": scope["method"],
                    "http_path": scope["path"],
                    "http_status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )

        finally:
            request_id_context.reset(token)
