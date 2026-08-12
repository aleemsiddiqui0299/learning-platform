import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base_project.settings')

app = Celery(
    'base_project',
    broker=os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
    backend=os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0') # ← CRITICAL FIX: Forces task results caching!
)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()