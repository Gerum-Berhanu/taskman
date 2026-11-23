from celery import Celery
from celery.signals import after_setup_logger

from app.core.config import settings
from app.observability.setup import setup_logging


@after_setup_logger.connect
def _configure_worker_logging(**_kwargs) -> None:
    setup_logging()


celery_app = Celery(
    "taskman",
    broker=settings.rabbitmq_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    timezone="UTC",
    beat_schedule={
        "purge-expired-client-sessions": {
            "task": "taskman.purge_expired_client_sessions",
            "schedule": float(settings.session_purge_interval_seconds),
        },
    },
)
