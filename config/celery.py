import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')  # or use decouple here

app = Celery('tcsp')  # your project name
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
