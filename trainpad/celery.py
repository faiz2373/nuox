from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# creates a celery application using Django settings and find file named task.py
# setting the Django settings module.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trainpad.settings')
app = Celery('trainpad')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Looks up for task modules in Django applications and loads them
app.autodiscover_tasks()