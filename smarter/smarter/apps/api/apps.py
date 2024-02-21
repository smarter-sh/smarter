# -*- coding: utf-8 -*-
"""This module is used to configure the Smarter Admin app."""
from django.apps import AppConfig


class ApiConfig(AppConfig):
    """AdminConfig class. This class is used to configure the Smarter Admin app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.api"
