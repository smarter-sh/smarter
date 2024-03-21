# -*- coding: utf-8 -*-
"""Celery configuration for smarter app."""
from __future__ import absolute_import, unicode_literals

import os

from celery import Celery


# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")
environment = os.getenv("ENVIRONMENT")
os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings." + environment


app = Celery("smarter")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
