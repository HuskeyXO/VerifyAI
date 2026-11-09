from app.core.logging_config import configure_logging

configure_logging()
from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "verifyai",
    broker=settings.redis_url,
    include=["app.tasks.verification"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_ignore_result=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
)
