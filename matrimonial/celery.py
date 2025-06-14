# matrimonial/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrimonial.settings')

app = Celery('matrimonial') # The app instance is named 'app'
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()