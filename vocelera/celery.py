import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vocelera.settings')

app = Celery('vocelera')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()