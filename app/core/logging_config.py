
import json
import logging
import logging.config
import sys

from contextvars import ContextVar
from datetime import datetime, timezone


request_id_context = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Attach the current HTTP request ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


class JsonFormatter(logging.Formatter):
    """Format application logs as structured JSON."""

    EXTRA_FIELDS = (
        "request_id",
        "http_method",
        "http_path",
        "http_status_code",
        "duration_ms",
        "verification_id",
        "task_id",
        "search_query",
        "article_count",
        "candidate_count",
        "evidence_relation",
        "relevance_score",
        "quote_matches",
        "saved_evidence_count",
        "retry_count",
        "retry_delay",
        "verdict",
        "job_status",
        "query_index",
        "valid_article_index",
        "has_quote",
        "has_reason",
    )

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        for field in self.EXTRA_FIELDS:
            value = getattr(record, field, None)

            if value is not None:
                log_data[field] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(log_data, default=str, ensure_ascii=False)


def configure_logging() -> None:
    """Configure consistent application-wide JSON logging."""

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "filters": {
            "request_context": {
                "()": RequestIdFilter,
            },
        },

        "formatters": {
            "json": {
                "()": JsonFormatter,
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json",
                "filters": ["request_context"],
            },
        },

        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },

        "loggers": {
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "celery": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    })
