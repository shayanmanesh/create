from celery import Celery
from app.config import settings
import os

# Create Celery instance
celery_app = Celery(
    "create-ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['app.tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    'app.tasks.process_creation': {'queue': 'creation'},
    'app.tasks.send_email': {'queue': 'email'},
    'app.tasks.update_analytics': {'queue': 'analytics'},
}

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'update-surge-pricing': {
        'task': 'app.tasks.update_surge_pricing',
        'schedule': 60.0,  # Every minute
    },
    'cleanup-expired-creations': {
        'task': 'app.tasks.cleanup_expired_creations',
        'schedule': 3600.0,  # Every hour
    },
    'calculate-viral-metrics': {
        'task': 'app.tasks.calculate_viral_metrics',
        'schedule': 300.0,  # Every 5 minutes
    },
}

if __name__ == '__main__':
    celery_app.start()