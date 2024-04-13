"""Django application configuration for the chatapp"""

from django.apps import AppConfig


class ChatAppConfig(AppConfig):
    """ChatApp application configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.chatapp"
