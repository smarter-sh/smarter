# -*- coding: utf-8 -*-
"""Define the chatbot app configuration."""
from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    """Define the chatbot app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.chatbot"
    verbose_name = "ChatBot"

    # pylint: disable=C0415,W0611
    def ready(self):
        """Handle signals."""
        import smarter.apps.chatbot.receivers  # noqa
        import smarter.apps.chatbot.signals  # noqa
