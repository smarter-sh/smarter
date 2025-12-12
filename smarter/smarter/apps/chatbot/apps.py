"""Django Config for the ChatBot app."""

import logging

from django.apps import AppConfig

from .const import namespace as app_name


logger = logging.getLogger(__name__)


class ChatbotConfig(AppConfig):
    """Django Config for the ChatBot app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
    verbose_name = "Smarter ChatBot"

    # pylint: disable=C0415,W0611
    def ready(self):
        """Handle signals."""
        from . import receivers  # noqa
        from . import signals  # noqa

        logger.info("ChatBot app ready: signals and receivers imported")
