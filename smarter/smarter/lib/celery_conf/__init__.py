"""
The Smarter platform's Celery app.

It is configured from the Django settings whose names start with ``CELERY_``, and finds the
``tasks`` modules of every installed Django app.
"""

from celery import Celery

APP = Celery("smarter")
"""The Celery app that the Smarter workers and Celery Beat run."""
APP.conf.task_protocol = 1
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
APP.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django APP configs.
APP.autodiscover_tasks()

APP.conf.broker_connection_retry_on_startup = True
