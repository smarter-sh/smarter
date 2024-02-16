# -*- coding: utf-8 -*-
"""PluginMeta app configuration."""

from django.apps import AppConfig


class PluginConfig(AppConfig):
    """PluginMeta app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.plugin"
