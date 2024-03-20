# -*- coding: utf-8 -*-
# __init__.py
"""Celery configuration for smarter app."""
from __future__ import absolute_import, unicode_literals

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .smarter_celery import app as celery_app


__all__ = ("celery_app",)
