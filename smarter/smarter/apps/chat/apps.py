# -*- coding: utf-8 -*-
"""Django app for the OpenAI Function Calling app."""
from django.apps import AppConfig


class ChatConfig(AppConfig):
    """Django Config for the OpenAI Function Calling app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.chat"
    verbose_name = "Chat"

    # pylint: disable=C0415,W0611
    def ready(self):
        """Handle signals."""
        # import .receivers  # noqa
        # import .signals  # noqa
