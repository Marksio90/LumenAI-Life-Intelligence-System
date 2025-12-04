"""
Celery Application Configuration

Handles background task processing with RabbitMQ.
"""

import os
import logging
from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# Get configuration from environment
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

# Redis for result backend
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("CELERY_REDIS_DB", "1")

# Build broker URL
broker_url = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Create Celery application
celery_app = Celery(
    "lumenai",
    broker=broker_url,
    backend=result_backend,
    include=[
        "backend.tasks.file_processing_tasks",
        "backend.tasks.llm_tasks",
        "backend.tasks.rag_tasks",
        "backend.tasks.maintenance_tasks"
    ]
)

# Configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit

    # Task routing
    task_routes={
        "backend.tasks.file_processing_tasks.*": {"queue": "file_processing"},
        "backend.tasks.llm_tasks.*": {"queue": "llm"},
        "backend.tasks.rag_tasks.*": {"queue": "rag"},
        "backend.tasks.maintenance_tasks.*": {"queue": "maintenance"}
    },

    # Task priorities
    task_queue_max_priority=10,
    task_default_priority=5,

    # Results
    result_expires=3600,  # 1 hour
    result_extended=True,

    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,

    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Beat schedule (periodic tasks)
    beat_schedule={
        # Clean up old files every day at 2 AM
        "cleanup-old-files": {
            "task": "backend.tasks.maintenance_tasks.cleanup_old_files",
            "schedule": crontab(hour=2, minute=0),
            "args": (30,)  # older than 30 days
        },
        # Clean up temp voice files every 6 hours
        "cleanup-voice-files": {
            "task": "backend.tasks.maintenance_tasks.cleanup_voice_files",
            "schedule": crontab(hour="*/6", minute=0),
            "args": (24,)  # older than 24 hours
        },
        # Update RAG statistics every hour
        "update-rag-stats": {
            "task": "backend.tasks.rag_tasks.update_statistics",
            "schedule": crontab(hour="*", minute=0)
        },
        # Health check every 5 minutes
        "health-check": {
            "task": "backend.tasks.maintenance_tasks.health_check",
            "schedule": crontab(minute="*/5")
        }
    }
)

logger.info(
    f"Celery app configured: broker={broker_url}, "
    f"backend={result_backend}"
)


# Utility functions

def get_celery_app() -> Celery:
    """Get the configured Celery application."""
    return celery_app


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery setup."""
    return f"Request: {self.request!r}"
