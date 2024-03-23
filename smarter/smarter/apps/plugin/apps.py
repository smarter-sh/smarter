# -*- coding: utf-8 -*-
"""Plugin app configuration."""
from django.apps import AppConfig


class PluginConfig(AppConfig):
    """PluginMeta app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.plugin"

    # pylint: disable=import-outside-toplevel,unused-import
    def ready(self):
        """Import signals."""
        # import .receivers  # noqa
        # import .signals  # noqa
