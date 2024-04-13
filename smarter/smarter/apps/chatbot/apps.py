"""Django Config for the ChatBot app."""

from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    """Django Config for the ChatBot app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.chatbot"
    verbose_name = "ChatBot"

    # pylint: disable=C0415,W0611
    def ready(self):
        """Handle signals."""
        from . import receivers  # noqa
        from . import signals  # noqa
