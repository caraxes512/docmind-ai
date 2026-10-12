"""Celery application instance. Broker and result backend are both Redis
(Step 1 decision) — a single Redis instance is sufficient at this scale;
splitting broker/backend onto separate instances is a scaling step to
revisit if queue depth and result-storage contention start competing for
the same instance's resources.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "docmind",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.repository_ingestion_tasks",
        "app.tasks.documentation_tasks",
        "app.tasks.export_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    # Soft/hard time limits: repository ingestion and doc generation can run
    # for minutes, but a runaway task (stuck LLM call, infinite loop in a
    # parser) must not hold a worker slot indefinitely.
    task_soft_time_limit=15 * 60,
    task_time_limit=20 * 60,
    worker_prefetch_multiplier=1,  # long-running tasks — don't let one worker hoard the queue
)
