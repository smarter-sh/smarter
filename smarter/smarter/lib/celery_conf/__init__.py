# -*- coding: utf-8 -*-
"""Celery configuration for smarter APP."""

from celery import Celery


APP = Celery("smarter")
APP.conf.task_protocol = 1
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
APP.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django APP configs.
APP.autodiscover_tasks()

try:
    with APP.connection() as conn:
        conn.ensure_connection(max_retries=3)
    print("Successfully connected to celery broker url: ", APP.conf.broker_url)
# pylint: disable=broad-except
except Exception as e:
    print(e)
