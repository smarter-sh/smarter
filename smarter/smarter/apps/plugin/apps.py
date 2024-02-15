# -*- coding: utf-8 -*-
"""Plugin app configuration."""

from django.apps import AppConfig


class PluginConfig(AppConfig):
    """Plugin app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.plugin"
